import json
import math
import os
import re
import time
from collections import defaultdict
from datetime import datetime

import frappe
from bs4 import BeautifulSoup
from frappe.utils import update_progress_bar


class FullTextSearch:
	def __init__(self, verbose=False, max_results=200):
		self.current_time = int(time.time())
		self.redis = frappe.cache()
		self._index_loaded = False
		self.doc_timestamps = {}
		self.doc_contents = {}
		self.verbose = verbose
		self.log_file = os.path.join(frappe.utils.get_site_path(), "logs", "search.log")
		os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
		self.max_results = max_results
		self.matched_words = defaultdict(set)
		self.matched_word_variations = defaultdict(set)  # Track variations per document
		self.matched_positions = defaultdict(dict)  # Track positions of matched words
		self.stop_words = {
			"a",
			"an",
			"and",
			"are",
			"as",
			"at",
			"be",
			"by",
			"for",
			"from",
			"has",
			"he",
			"in",
			"is",
			"it",
			"its",
			"of",
			"on",
			"that",
			"the",
			"to",
			"was",
			"were",
			"will",
			"with",
			"this",
			"but",
			"they",
			"have",
			"had",
			"what",
			"when",
			"where",
			"who",
			"which",
			"why",
			"how",
			"all",
			"any",
			"both",
			"each",
			"few",
			"more",
			"most",
			"other",
			"some",
			"such",
			"no",
			"nor",
			"not",
			"only",
			"own",
			"same",
			"so",
			"than",
			"too",
			"very",
			"can",
			"just",
			"should",
			"now",
			"i",
			"you",
			"your",
			"we",
			"my",
			"me",
			"she",
			"them",
			"their",
		}
		self.redis_prefix = "fts:"

	def _debug(self, *args):
		"""Log debug messages to file if verbose mode is enabled"""
		if self.verbose:
			timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
			message = " ".join(str(arg) for arg in args)
			with open(self.log_file, "a") as f:
				f.write(f"[{timestamp}] {message}\n")

	def index_documents(self, documents):
		"""Build the index from documents and save it to Redis."""
		self._build_indexes(documents)
		self._save_index_to_redis()
		self._index_loaded = True

	def index_exists(self):
		required_keys = ["inverted_index", "doc_lengths", "document_count"]

		for key in required_keys:
			if not self.redis.get_value(self._get_redis_key(key)):
				return False

		return True

	def _get_redis_key(self, key):
		return f"{self.redis_prefix}{key}"

	def _process_document_content(self, doc_id, title, content, timestamp):
		"""Process a document's content and prepare word frequencies for indexing."""
		processed_content = self._process_content(content)

		# Store document contents and timestamp
		self.doc_timestamps[doc_id] = timestamp
		self.doc_contents[doc_id] = {
			"title": title,
			"content": processed_content,
		}

		# Index title and content words
		title_words = re.findall(r"\w+", title.lower())
		content_words = re.findall(r"\w+", processed_content.lower())

		# Store title words
		self.title_words = getattr(self, "title_words", {})
		self.title_words[doc_id] = title_words

		# Process word frequencies and positions
		word_freq = defaultdict(lambda: {"title": 0, "content": 0})
		word_positions = defaultdict(lambda: {"title": [], "content": []})

		# Update trigrams, word frequencies and positions
		title_pos = 0
		for word in title_words:
			word_freq[word]["title"] += 1
			word_positions[word]["title"].append(title_pos)
			title_pos += 1
			for trigram in self._generate_trigrams(word):
				self.trigram_index[trigram].add(word)

		content_pos = 0
		for word in content_words:
			word_freq[word]["content"] += 1
			word_positions[word]["content"].append(content_pos)
			content_pos += 1
			for trigram in self._generate_trigrams(word):
				self.trigram_index[trigram].add(word)

		# Calculate document length
		total_words = len(title_words) * 3 + len(content_words)
		self.doc_lengths[doc_id] = total_words

		return word_freq, word_positions, total_words

	def _save_index_to_redis(self):
		"""Serialize and save the index to Redis with consistent key naming"""
		data = {
			"inverted_index": json.dumps(self.inverted_index),
			"trigram_index": json.dumps({k: list(v) for k, v in self.trigram_index.items()}),
			"doc_lengths": self.doc_lengths,
			"avg_doc_length": self.avg_doc_length,
			"document_count": self.document_count,
			"doc_timestamps": self.doc_timestamps,
			"title_words": {k: list(v) for k, v in self.title_words.items()},
			"doc_contents": self.doc_contents,
			"word_positions": json.dumps(self.word_positions),
		}

		for key, value in data.items():
			self.redis.set_value(self._get_redis_key(key), value)

	def _build_indexes(self, documents):
		"""Build inverted index for BM25 and trigram index for fuzzy matching."""
		self.documents = documents
		total_docs = len(documents)
		self.document_count = total_docs
		self.inverted_index = defaultdict(list)
		self.trigram_index = defaultdict(set)
		self.doc_lengths = {}
		self.word_positions = defaultdict(lambda: defaultdict(dict))
		total_length = 0

		for i, doc in enumerate(self.documents):
			doc_id = doc["id"]
			word_freq, positions, doc_length = self._process_document_content(
				doc_id, doc["title"], doc["content"], doc["timestamp"]
			)
			total_length += doc_length

			for word, freqs in word_freq.items():
				total_freq = freqs["title"] * 3 + freqs["content"]
				self.inverted_index[word].append((doc_id, total_freq))
				self.word_positions[word][doc_id] = positions[word]

			if not hasattr(frappe.local, "request"):
				update_progress_bar("Indexing documents", i + 1, total_docs, absolute=True)

		if not hasattr(frappe.local, "request"):
			print()

		self.avg_doc_length = total_length / len(self.documents)

	def _process_content(self, content):
		soup = BeautifulSoup(content, "html.parser")
		text = soup.get_text(separator=" ").strip()  # remove tags
		text = re.sub(r"https?://[^\s]+", "[link]", text)  # replace links
		text = re.sub(r"\s+", " ", text).strip()  # normalize whitespace
		return text

	def _load_index_from_redis(self):
		"""Load and deserialize the index from Redis with consistent key naming"""
		if self._index_loaded:
			return

		data = {
			key: self.redis.get_value(self._get_redis_key(key))
			for key in [
				"inverted_index",
				"trigram_index",
				"doc_lengths",
				"avg_doc_length",
				"document_count",
				"doc_timestamps",
				"title_words",
				"doc_contents",
				"word_positions",
			]
		}

		if data["inverted_index"]:
			self.inverted_index = defaultdict(list, json.loads(data["inverted_index"]))
		if data["trigram_index"]:
			trigram_dict = json.loads(data["trigram_index"])
			self.trigram_index = defaultdict(set, {k: set(v) for k, v in trigram_dict.items()})
		if data["doc_lengths"]:
			self.doc_lengths = data["doc_lengths"]
		if data["avg_doc_length"]:
			self.avg_doc_length = data["avg_doc_length"]
		if data["document_count"]:
			self.document_count = data["document_count"]
		if data["doc_timestamps"]:
			self.doc_timestamps = data["doc_timestamps"]
		if data["title_words"]:
			self.title_words = {k: set(v) for k, v in data["title_words"].items()}
		if data["doc_contents"]:
			self.doc_contents = data["doc_contents"]
		if data["word_positions"]:
			self.word_positions = defaultdict(lambda: defaultdict(dict), json.loads(data["word_positions"]))

		self._index_loaded = True

	def _generate_trigrams(self, word):
		"""Generate trigrams for a given word."""
		word = f"  {word}  "
		return [word[i : i + 3] for i in range(len(word) - 2)]

	def _find_fuzzy_matches(self, query_word, threshold=0.4):
		"""Find words with similar trigrams to the query word."""
		query_trigrams = set(self._generate_trigrams(query_word))
		candidate_words = defaultdict(int)

		for trigram in query_trigrams:
			if trigram in self.trigram_index:
				for word in self.trigram_index[trigram]:
					candidate_words[word] += 1

		results = []
		for word, overlap in candidate_words.items():
			jaccard_similarity = overlap / (
				len(query_trigrams) + len(self._generate_trigrams(word)) - overlap
			)
			if jaccard_similarity >= threshold:
				results.append((word, jaccard_similarity))

		results = sorted(results, key=lambda x: x[1], reverse=True)
		self._debug(f"Fuzzy matches for '{query_word}': {results[:3]}")
		return results

	def _calculate_proximity_score(self, doc_id, query_words):
		"""Calculate proximity score based on the closeness of query terms in the document."""
		if len(query_words) < 2:
			return 1.0  # No proximity boost for single word queries

		# Filter to words that actually appear in the document
		filtered_words = [
			w for w in query_words if w in self.word_positions and doc_id in self.word_positions[w]
		]
		if len(filtered_words) < 2:
			return 1.0  # Need at least 2 words to calculate proximity

		# Get all positions for each word
		all_positions = []
		for word in filtered_words:
			word_pos = []
			if "title" in self.word_positions[word][doc_id]:
				# Title positions get a bonus by multiplying by 0.5
				word_pos.extend([p * 0.5 for p in self.word_positions[word][doc_id]["title"]])
			if "content" in self.word_positions[word][doc_id]:
				word_pos.extend(self.word_positions[word][doc_id]["content"])
			all_positions.append(word_pos)

		# Calculate minimum span covering all query terms
		min_span = float("inf")

		# Only calculate spans if we have positions for all words
		if all(pos for pos in all_positions):
			# For each position of the first word
			for pos1 in all_positions[0]:
				# Find closest positions of other words
				max_distance = 0
				for positions in all_positions[1:]:
					# Find the closest position
					closest = min(positions, key=lambda x: abs(x - pos1))
					distance = abs(closest - pos1)
					max_distance = max(max_distance, distance)

				# Update minimum span
				min_span = min(min_span, max_distance)

		# Convert span to score (smaller spans get higher scores)
		if min_span == float("inf"):
			return 1.0

		# Logarithmic scaling to prevent excessive influence
		proximity_score = 1.0 + 0.25 * math.log(1.0 + 10.0 / max(1, min_span))
		return proximity_score

	def _bm25_score(self, query_words, title_only=False):
		"""Calculate BM25 scores for documents given the query words."""
		# Filter out stop words but keep track of original words
		filtered_map = [(w, orig) for orig in query_words if (w := orig.lower()) not in self.stop_words]

		if not filtered_map:
			# If all words are stop words, use original query
			filtered_map = [(w.lower(), w) for w in query_words]

		self._debug(f"\nCalculating BM25 scores for words: {[w for w, _ in filtered_map]}")
		doc_scores = defaultdict(float)
		self.matched_words.clear()  # Reset matched words for new search
		self.matched_word_variations.clear()  # Reset variations
		self.matched_positions.clear()  # Reset positions
		num_docs = self.document_count
		k1, b = 1.2, 0.75  # BM25 parameters
		self.score_components = defaultdict(lambda: {"bm25": 0})

		for filtered, original in filtered_map:
			if filtered not in self.inverted_index:
				self._debug(f"Word '{filtered}' not found in index")
				continue

			# For title_only search, only consider documents where the word appears in title
			docs_with_word = []
			if title_only:
				docs_with_word = [
					(doc_id, freq)
					for doc_id, freq in self.inverted_index[filtered]
					if doc_id in self.title_words
					and filtered in set(w.lower() for w in self.title_words[doc_id])
				]
			else:
				docs_with_word = self.inverted_index[filtered]

			num_docs_with_word = len(docs_with_word)
			if num_docs_with_word == 0:
				continue

			idf = math.log((num_docs - num_docs_with_word + 0.5) / (num_docs_with_word + 0.5) + 1)
			self._debug(f"\nWord: '{filtered}'")
			self._debug(f"Found in {num_docs_with_word} documents")
			self._debug(f"IDF score: {idf:.4f}")

			for doc_id, freq in docs_with_word:
				doc_len = self.doc_lengths[doc_id]
				tf = freq
				score = idf * ((tf * (k1 + 1)) / (tf + k1 * (1 - b + b * (doc_len / self.avg_doc_length))))
				doc_scores[doc_id] += score
				self.matched_words[doc_id].add(filtered)
				self.matched_word_variations[doc_id].update([filtered, original])

				# Store positions for proximity scoring
				if doc_id in self.word_positions.get(filtered, {}):
					self.matched_positions[doc_id][filtered] = self.word_positions[filtered][doc_id]

				self.score_components[doc_id]["bm25"] += score

		return doc_scores

	def _boost_proximity(self, doc_scores, query_words):
		"""Apply boost based on proximity of query terms in documents."""
		self._debug("\nApplying proximity boost:")
		# Filter out stop words but keep track of original words
		filtered_words = [w.lower() for w in query_words if w.lower() not in self.stop_words]

		if not filtered_words:
			filtered_words = [w.lower() for w in query_words]

		if len(filtered_words) < 2:
			self._debug("Skipping proximity boost for single-word query")
			return doc_scores

		boosted_scores = {}
		for doc_id, score in doc_scores.items():
			proximity_score = self._calculate_proximity_score(doc_id, filtered_words)
			boosted_scores[doc_id] = score * proximity_score
			self.score_components[doc_id]["proximity"] = proximity_score
			self._debug(
				f"Doc {doc_id}: Proximity boost {proximity_score:.3f}x ({score:.4f} ->"
				" {boosted_scores[doc_id]:.4f})"
			)
		return boosted_scores

	def _boost_recency(self, doc_scores, alpha=0.001):
		"""Boost scores based on recency (documents with newer timestamps get a slight boost)."""
		self._debug("\nApplying recency boost:")
		alpha = 0.005
		boosted_scores = {}
		for doc_id, score in doc_scores.items():
			age = self.current_time - self.doc_timestamps.get(doc_id, 0)
			recency_boost = 1 / (1 + alpha * age)  # The more recent, the higher the boost
			boosted_scores[doc_id] = score * recency_boost
			self.score_components[doc_id]["recency_boost"] = recency_boost
			self._debug(f"Doc {doc_id}: age={age / 86400:.1f} days")
			self._debug(f"  Score: {score:.4f} -> {boosted_scores[doc_id]:.4f} (boost={recency_boost:.3f}x)")
		return boosted_scores

	def _boost_title_matches(self, query_words, doc_scores):
		"""Apply additional boost for documents with exact or partial title matches"""
		self._debug("\nApplying title boost:")
		# Use non-stop words for title matching
		filtered_words = [w for w in query_words if w not in self.stop_words]
		if not filtered_words:
			filtered_words = query_words

		for doc_id in doc_scores:
			if doc_id in self.title_words:
				title_words = self.title_words[doc_id]

				# Calculate what portion of query matches the title
				matching_words = sum(1 for qw in filtered_words if qw in title_words)
				if matching_words > 0:
					match_ratio = matching_words / len(filtered_words)
					# Apply exponential boost for better title matches
					title_boost = 1 + (match_ratio**2) * 2
					old_score = doc_scores[doc_id]
					doc_scores[doc_id] *= title_boost
					self.score_components[doc_id]["title_boost"] = title_boost
					self._debug(
						f"""Doc {doc_id} ({title_words}): """
						"""{matching_words}/{len(filtered_words)} words match title"""
					)
					self._debug(
						f"  Score: {old_score:.4f} -> {doc_scores[doc_id]:.4f} (boost={title_boost:.2f}x)"
					)

		return doc_scores

	def _highlight_text(self, text, doc_id):
		"""Wrap matching words in <mark> tags, but only those that contributed to scoring"""
		if doc_id not in self.matched_word_variations:
			return text

		text_words = re.findall(r"[\w]+|[^\w]+", text)  # Split keeping separators
		result = []
		matched_variations = self.matched_word_variations[doc_id]

		for word in text_words:
			if word.lower() in matched_variations:
				result.append(f"<mark>{word}</mark>")
			else:
				result.append(word)
		return "".join(result)

	def _create_preview(self, text, doc_id, context_chars=50):
		"""Create a preview of text showing context around matched words with highlighting"""
		if doc_id not in self.matched_word_variations:
			preview = " ".join(text.split()[:10])
			return preview + "..." if len(text.split()) > 10 else preview

		text = text.replace("\n", " ")
		words = text.split(" ")
		matches = []
		matched_variations = self.matched_word_variations[doc_id]

		# Find all occurrences of matched words
		for i, word in enumerate(words):
			if word.lower() in matched_variations:
				start = max(0, i - 5)
				end = min(len(words), i + 6)
				matches.append((start, end, i))

		if not matches:
			# If no matches, return first few words
			preview = " ".join(words[:10])
			return preview + "..." if len(words) > 10 else preview

		# Merge overlapping ranges
		matches.sort()
		merged = []
		current_start, current_end, _ = matches[0]

		for start, end, _ in matches[1:]:
			if start <= current_end:
				current_end = max(current_end, end)
			else:
				merged.append((current_start, current_end))
				current_start, current_end = start, end

		merged.append((current_start, current_end))

		# Create preview text with highlighting
		preview = []
		for start, end in merged:
			snippet = []
			for i in range(start, end):
				word = words[i]
				if any(qw in word.lower() for qw in matched_variations):
					snippet.append(f"<mark>{word}</mark>")
				else:
					snippet.append(word)
			preview.append(" ".join(snippet))

		return "..." + "...".join(preview) + "..."

	def search(self, query, title_only=False):
		"""Main search function with improved title matching and content highlighting."""
		start_time = time.time()
		self._debug(f"\n=== Search Query: '{query}' (title_only: {title_only}) ===")
		self._load_index_from_redis()

		query_words = re.findall(r"\w+", query.lower())
		self._debug(f"Query words: {query_words}")

		corrected_query_words = []
		self._debug("\nFuzzy matching:")
		for word in query_words:
			matches = self._find_fuzzy_matches(word)
			corrected = matches[0][0] if matches else word
			corrected_query_words.append(corrected)
			if corrected != word:
				self._debug(f"Corrected '{word}' to '{corrected}'")

		# Calculate base BM25 scores
		doc_scores = self._bm25_score(corrected_query_words, title_only)
		self._debug("\nInitial BM25 scores:")
		for doc_id, score in sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)[:3]:
			title = self.doc_contents[doc_id]["title"]
			content = self.doc_contents[doc_id]["content"]
			self._debug(f"Doc {doc_id}: {score:.4f}")
			self._debug(f"  Title: {title[:50]}")
			self._debug(f"  Content: {content[:100]}")

		# Apply proximity boost as a separate step
		doc_scores = self._boost_proximity(doc_scores, corrected_query_words)
		self._debug("\nScores after proximity boost:")
		for doc_id, score in sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)[:3]:
			title = self.doc_contents[doc_id]["title"]
			content = self.doc_contents[doc_id]["content"]
			self._debug(f"Doc {doc_id}: {score:.4f}")
			self._debug(f"  Title: {title[:50]}")
			self._debug(f"  Content: {content[:100]}")

		doc_scores = self._boost_title_matches(query_words, doc_scores)
		final_scores = self._boost_recency(doc_scores)
		total_matches = len(final_scores)

		self._debug("\nSearch results summary:")
		results = []
		for doc_id, score in sorted(final_scores.items(), key=lambda x: x[1], reverse=True)[
			: self.max_results
		]:
			if doc_id in self.doc_contents:
				doc_content = self.doc_contents[doc_id]
				components = self.score_components[doc_id]
				self._debug(
					f"Doc {doc_id}: {doc_content['title'][:50]}\n"
					f"  Final score: {score:.4f}\n"
					f"  BM25 score: {components['bm25']:.4f}\n"
					f"  Proximity boost: {components.get('proximity', 1.0):.2f}x\n"
					f"  Title boost: {components.get('title_boost', 1.0):.2f}x\n"
					f"  Recency boost: {components.get('recency_boost', 1.0):.3f}x\n"
					f"  Matched words: {sorted(self.matched_words[doc_id])}\n"
					f"  Word variations: {sorted(self.matched_word_variations[doc_id])}\n"
				)
				result = {
					"id": doc_id,
					"title": self._highlight_text(doc_content["title"], doc_id),
					"score": score,
					"timestamp": self.doc_timestamps[doc_id],
				}
				if not title_only:
					result["content"] = self._create_preview(doc_content["content"], doc_id)
				results.append(result)

		duration = time.time() - start_time
		corrected_words = (
			dict(zip(query_words, corrected_query_words, strict=True))
			if any(w != c for w, c in zip(query_words, corrected_query_words, strict=True))
			else None
		)
		summary = {
			"duration": round(duration, 3),
			"total_matches": total_matches,
			"returned_matches": len(results),
			"corrected_words": corrected_words,
			"title_only": title_only,
		}

		self._debug(f"\nReturning top {len(results)} results out of {len(final_scores)} matches")
		return {"results": results, "summary": summary}

	def index_document(self, document):
		"""Add a single document to the index."""
		self._load_index_from_redis()
		doc_id = document["id"]

		# Use helper method to process document content
		word_freq, word_positions, total_words = self._process_document_content(
			doc_id, document["title"], document["content"], document["timestamp"]
		)

		# Update inverted index
		for word, freqs in word_freq.items():
			total_freq = freqs["title"] * 3 + freqs["content"]
			if word in self.inverted_index:
				self.inverted_index[word] = [(d, f) for d, f in self.inverted_index[word] if d != doc_id]
			self.inverted_index[word].append((doc_id, total_freq))
			# Update word positions
			self.word_positions[word][doc_id] = word_positions[word]

		# Update document count and average length
		self.document_count = len(self.doc_lengths)
		self.avg_doc_length = sum(self.doc_lengths.values()) / self.document_count

		self._save_index_to_redis()

	def remove_document(self, doc_id):
		"""Remove a document from the index."""
		self._load_index_from_redis()

		if doc_id not in self.doc_lengths:
			return

		# Remove from doc_timestamps and doc_contents
		self.doc_timestamps.pop(doc_id, None)
		self.doc_contents.pop(doc_id, None)

		# Remove from title_words
		self.title_words.pop(doc_id, None)

		# Remove document from inverted index
		for word in list(self.inverted_index.keys()):
			self.inverted_index[word] = [(d, f) for d, f in self.inverted_index[word] if d != doc_id]
			if not self.inverted_index[word]:
				del self.inverted_index[word]

		# Remove from word_positions
		for word in list(self.word_positions.keys()):
			if doc_id in self.word_positions[word]:
				del self.word_positions[word][doc_id]
			if not self.word_positions[word]:
				del self.word_positions[word]

		# Remove from doc_lengths
		self.doc_lengths.pop(doc_id, None)

		# Update document count and average length
		self.document_count = len(self.doc_lengths)
		if self.document_count > 0:
			total_length = sum(self.doc_lengths.values())
			self.avg_doc_length = total_length / self.document_count
		else:
			self.avg_doc_length = 0

		self._save_index_to_redis()
