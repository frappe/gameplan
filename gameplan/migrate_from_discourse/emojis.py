# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals

def get_emoji(name):
	for emoji in emojis:
		if name == emoji['name']:
			codes = emoji['code'].split('-')
			ints = [int(d, 16) for d in codes]
			uni = [chr(d) for d in ints]
			return u''.join(uni)

emojis = [
  {
	"code": "1f600",
	"name": "grinning"
  },
  {
	"code": "1f62c",
	"name": "grimacing"
  },
  {
	"code": "1f601",
	"name": "grin"
  },
  {
	"code": "1f602",
	"name": "joy"
  },
  {
	"code": "1f923",
	"name": "rofl"
  },
  {
	"code": "1f603",
	"name": "smiley"
  },
  {
	"code": "1f604",
	"name": "smile"
  },
  {
	"code": "1f605",
	"name": "sweat_smile"
  },
  {
	"code": "1f606",
	"name": "laughing"
  },
  {
	"code": "1f607",
	"name": "innocent"
  },
  {
	"code": "1f609",
	"name": "wink"
  },
  {
	"code": "1f60a",
	"name": "blush"
  },
  {
	"code": "1f642",
	"name": "slightly_smiling_face"
  },
  {
	"code": "1f643",
	"name": "upside_down_face"
  },
  {
	"code": "263a",
	"name": "relaxed"
  },
  {
	"code": "1f60b",
	"name": "yum"
  },
  {
	"code": "1f60c",
	"name": "relieved"
  },
  {
	"code": "1f60d",
	"name": "heart_eyes"
  },
  {
	"code": "1f618",
	"name": "kissing_heart"
  },
  {
	"code": "1f617",
	"name": "kissing"
  },
  {
	"code": "1f619",
	"name": "kissing_smiling_eyes"
  },
  {
	"code": "1f61a",
	"name": "kissing_closed_eyes"
  },
  {
	"code": "1f61c",
	"name": "stuck_out_tongue_winking_eye"
  },
  {
	"code": "1f61d",
	"name": "stuck_out_tongue_closed_eyes"
  },
  {
	"code": "1f61b",
	"name": "stuck_out_tongue"
  },
  {
	"code": "1f911",
	"name": "money_mouth_face"
  },
  {
	"code": "1f913",
	"name": "nerd_face"
  },
  {
	"code": "1f60e",
	"name": "sunglasses"
  },
  {
	"code": "1f921",
	"name": "clown_face"
  },
  {
	"code": "1f920",
	"name": "cowboy_hat_face"
  },
  {
	"code": "1f917",
	"name": "hugs"
  },
  {
	"code": "1f60f",
	"name": "smirk"
  },
  {
	"code": "1f636",
	"name": "no_mouth"
  },
  {
	"code": "1f610",
	"name": "neutral_face"
  },
  {
	"code": "1f611",
	"name": "expressionless"
  },
  {
	"code": "1f612",
	"name": "unamused"
  },
  {
	"code": "1f644",
	"name": "roll_eyes"
  },
  {
	"code": "1f914",
	"name": "thinking"
  },
  {
	"code": "1f925",
	"name": "lying_face"
  },
  {
	"code": "1f633",
	"name": "flushed"
  },
  {
	"code": "1f61e",
	"name": "disappointed"
  },
  {
	"code": "1f61f",
	"name": "worried"
  },
  {
	"code": "1f620",
	"name": "angry"
  },
  {
	"code": "1f621",
	"name": "rage"
  },
  {
	"code": "1f614",
	"name": "pensive"
  },
  {
	"code": "1f615",
	"name": "confused"
  },
  {
	"code": "1f641",
	"name": "slightly_frowning_face"
  },
  {
	"code": "2639",
	"name": "frowning_face"
  },
  {
	"code": "1f623",
	"name": "persevere"
  },
  {
	"code": "1f616",
	"name": "confounded"
  },
  {
	"code": "1f62b",
	"name": "tired_face"
  },
  {
	"code": "1f629",
	"name": "weary"
  },
  {
	"code": "1f624",
	"name": "triumph"
  },
  {
	"code": "1f62e",
	"name": "open_mouth"
  },
  {
	"code": "1f631",
	"name": "scream"
  },
  {
	"code": "1f628",
	"name": "fearful"
  },
  {
	"code": "1f630",
	"name": "cold_sweat"
  },
  {
	"code": "1f62f",
	"name": "hushed"
  },
  {
	"code": "1f626",
	"name": "frowning_with_open_mouth"
  },
  {
	"code": "1f627",
	"name": "anguished"
  },
  {
	"code": "1f622",
	"name": "cry"
  },
  {
	"code": "1f625",
	"name": "disappointed_relieved"
  },
  {
	"code": "1f924",
	"name": "drooling_face"
  },
  {
	"code": "1f62a",
	"name": "sleepy"
  },
  {
	"code": "1f613",
	"name": "sweat"
  },
  {
	"code": "1f62d",
	"name": "sob"
  },
  {
	"code": "1f635",
	"name": "dizzy_face"
  },
  {
	"code": "1f632",
	"name": "astonished"
  },
  {
	"code": "1f910",
	"name": "zipper_mouth_face"
  },
  {
	"code": "1f922",
	"name": "nauseated_face"
  },
  {
	"code": "1f927",
	"name": "sneezing_face"
  },
  {
	"code": "1f637",
	"name": "mask"
  },
  {
	"code": "1f912",
	"name": "face_with_thermometer"
  },
  {
	"code": "1f915",
	"name": "face_with_head_bandage"
  },
  {
	"code": "1f634",
	"name": "sleeping"
  },
  {
	"code": "1f4a4",
	"name": "zzz"
  },
  {
	"code": "1f4a9",
	"name": "poop"
  },
  {
	"code": "1f608",
	"name": "smiling_imp"
  },
  {
	"code": "1f47f",
	"name": "imp"
  },
  {
	"code": "1f479",
	"name": "japanese_ogre"
  },
  {
	"code": "1f47a",
	"name": "japanese_goblin"
  },
  {
	"code": "1f480",
	"name": "skull"
  },
  {
	"code": "1f47b",
	"name": "ghost"
  },
  {
	"code": "1f47d",
	"name": "alien"
  },
  {
	"code": "1f916",
	"name": "robot"
  },
  {
	"code": "1f63a",
	"name": "smiley_cat"
  },
  {
	"code": "1f638",
	"name": "smile_cat"
  },
  {
	"code": "1f639",
	"name": "joy_cat"
  },
  {
	"code": "1f63b",
	"name": "heart_eyes_cat"
  },
  {
	"code": "1f63c",
	"name": "smirk_cat"
  },
  {
	"code": "1f63d",
	"name": "kissing_cat"
  },
  {
	"code": "1f640",
	"name": "scream_cat"
  },
  {
	"code": "1f63f",
	"name": "crying_cat_face"
  },
  {
	"code": "1f63e",
	"name": "pouting_cat"
  },
  {
	"code": "1f64c",
	"name": "raised_hands"
  },
  {
	"code": "1f44f",
	"name": "clap"
  },
  {
	"code": "1f44b",
	"name": "wave"
  },
  {
	"code": "1f919",
	"name": "call_me_hand"
  },
  {
	"code": "1f44d",
	"name": "+1"
  },
  {
	"code": "1f44e",
	"name": "-1"
  },
  {
	"code": "1f44a",
	"name": "facepunch"
  },
  {
	"code": "270a",
	"name": "fist"
  },
  {
	"code": "1f91b",
	"name": "fist_left"
  },
  {
	"code": "1f91c",
	"name": "fist_right"
  },
  {
	"code": "270c",
	"name": "v"
  },
  {
	"code": "1f44c",
	"name": "ok_hand"
  },
  {
	"code": "270b",
	"name": "raised_hand"
  },
  {
	"code": "1f91a",
	"name": "raised_back_of_hand"
  },
  {
	"code": "1f450",
	"name": "open_hands"
  },
  {
	"code": "1f4aa",
	"name": "muscle"
  },
  {
	"code": "1f64f",
	"name": "pray"
  },
  {
	"code": "1f91d",
	"name": "handshake"
  },
  {
	"code": "261d",
	"name": "point_up"
  },
  {
	"code": "1f446",
	"name": "point_up_2"
  },
  {
	"code": "1f447",
	"name": "point_down"
  },
  {
	"code": "1f448",
	"name": "point_left"
  },
  {
	"code": "1f449",
	"name": "point_right"
  },
  {
	"code": "1f595",
	"name": "fu"
  },
  {
	"code": "1f590",
	"name": "raised_hand_with_fingers_splayed"
  },
  {
	"code": "1f918",
	"name": "metal"
  },
  {
	"code": "1f91e",
	"name": "crossed_fingers"
  },
  {
	"code": "1f596",
	"name": "vulcan_salute"
  },
  {
	"code": "270d",
	"name": "writing_hand"
  },
  {
	"code": "1f933",
	"name": "selfie"
  },
  {
	"code": "1f485",
	"name": "nail_care"
  },
  {
	"code": "1f444",
	"name": "lips"
  },
  {
	"code": "1f445",
	"name": "tongue"
  },
  {
	"code": "1f442",
	"name": "ear"
  },
  {
	"code": "1f443",
	"name": "nose"
  },
  {
	"code": "1f441",
	"name": "eye"
  },
  {
	"code": "1f440",
	"name": "eyes"
  },
  {
	"code": "1f464",
	"name": "bust_in_silhouette"
  },
  {
	"code": "1f465",
	"name": "busts_in_silhouette"
  },
  {
	"code": "1f5e3",
	"name": "speaking_head"
  },
  {
	"code": "1f476",
	"name": "baby"
  },
  {
	"code": "1f466",
	"name": "boy"
  },
  {
	"code": "1f467",
	"name": "girl"
  },
  {
	"code": "1f468",
	"name": "man"
  },
  {
	"code": "1f469",
	"name": "woman"
  },
  {
	"code": "1f471-200d-2640-fe0f",
	"name": "blonde_woman"
  },
  {
	"code": "1f471",
	"name": "blonde_man"
  },
  {
	"code": "1f474",
	"name": "older_man"
  },
  {
	"code": "1f475",
	"name": "older_woman"
  },
  {
	"code": "1f472",
	"name": "man_with_gua_pi_mao"
  },
  {
	"code": "1f473-200d-2640-fe0f",
	"name": "woman_with_turban"
  },
  {
	"code": "1f473",
	"name": "man_with_turban"
  },
  {
	"code": "1f46e-200d-2640-fe0f",
	"name": "policewoman"
  },
  {
	"code": "1f46e",
	"name": "policeman"
  },
  {
	"code": "1f477-200d-2640-fe0f",
	"name": "construction_worker_woman"
  },
  {
	"code": "1f477",
	"name": "construction_worker_man"
  },
  {
	"code": "1f482-200d-2640-fe0f",
	"name": "guardswoman"
  },
  {
	"code": "1f482",
	"name": "guardsman"
  },
  {
	"code": "1f575-fe0f-200d-2640",
	"name": "female_detective"
  },
  {
	"code": "1f575",
	"name": "male_detective"
  },
  {
	"code": "1f469-200d-2695-fe0f",
	"name": "woman_health_worker"
  },
  {
	"code": "1f468-200d-2695-fe0f",
	"name": "man_health_worker"
  },
  {
	"code": "1f469-200d-1f33e",
	"name": "woman_farmer"
  },
  {
	"code": "1f468-200d-1f33e",
	"name": "man_farmer"
  },
  {
	"code": "1f469-200d-1f373",
	"name": "woman_cook"
  },
  {
	"code": "1f468-200d-1f373",
	"name": "man_cook"
  },
  {
	"code": "1f469-200d-1f393",
	"name": "woman_student"
  },
  {
	"code": "1f468-200d-1f393",
	"name": "man_student"
  },
  {
	"code": "1f469-200d-1f3a4",
	"name": "woman_singer"
  },
  {
	"code": "1f468-200d-1f3a4",
	"name": "man_singer"
  },
  {
	"code": "1f469-200d-1f3eb",
	"name": "woman_teacher"
  },
  {
	"code": "1f468-200d-1f3eb",
	"name": "man_teacher"
  },
  {
	"code": "1f469-200d-1f3ed",
	"name": "woman_factory_worker"
  },
  {
	"code": "1f468-200d-1f3ed",
	"name": "man_factory_worker"
  },
  {
	"code": "1f469-200d-1f4bb",
	"name": "woman_technologist"
  },
  {
	"code": "1f468-200d-1f4bb",
	"name": "man_technologist"
  },
  {
	"code": "1f469-200d-1f4bc",
	"name": "woman_office_worker"
  },
  {
	"code": "1f468-200d-1f4bc",
	"name": "man_office_worker"
  },
  {
	"code": "1f469-200d-1f527",
	"name": "woman_mechanic"
  },
  {
	"code": "1f468-200d-1f527",
	"name": "man_mechanic"
  },
  {
	"code": "1f469-200d-1f52c",
	"name": "woman_scientist"
  },
  {
	"code": "1f468-200d-1f52c",
	"name": "man_scientist"
  },
  {
	"code": "1f469-200d-1f3a8",
	"name": "woman_artist"
  },
  {
	"code": "1f468-200d-1f3a8",
	"name": "man_artist"
  },
  {
	"code": "1f469-200d-1f692",
	"name": "woman_firefighter"
  },
  {
	"code": "1f468-200d-1f692",
	"name": "man_firefighter"
  },
  {
	"code": "1f469-200d-2708-fe0f",
	"name": "woman_pilot"
  },
  {
	"code": "1f468-200d-2708-fe0f",
	"name": "man_pilot"
  },
  {
	"code": "1f469-200d-1f680",
	"name": "woman_astronaut"
  },
  {
	"code": "1f468-200d-1f680",
	"name": "man_astronaut"
  },
  {
	"code": "1f469-200d-2696-fe0f",
	"name": "woman_judge"
  },
  {
	"code": "1f468-200d-2696-fe0f",
	"name": "man_judge"
  },
  {
	"code": "1f936",
	"name": "mrs_claus"
  },
  {
	"code": "1f385",
	"name": "santa"
  },
  {
	"code": "1f47c",
	"name": "angel"
  },
  {
	"code": "1f930",
	"name": "pregnant_woman"
  },
  {
	"code": "1f478",
	"name": "princess"
  },
  {
	"code": "1f934",
	"name": "prince"
  },
  {
	"code": "1f470",
	"name": "bride_with_veil"
  },
  {
	"code": "1f935",
	"name": "person_in_tuxedo"
  },
  {
	"code": "1f3c3-200d-2640-fe0f",
	"name": "running_woman"
  },
  {
	"code": "1f3c3",
	"name": "running_man"
  },
  {
	"code": "1f6b6-200d-2640-fe0f",
	"name": "walking_woman"
  },
  {
	"code": "1f6b6",
	"name": "walking_man"
  },
  {
	"code": "1f483",
	"name": "dancer"
  },
  {
	"code": "1f57a",
	"name": "man_dancing"
  },
  {
	"code": "1f46f",
	"name": "dancing_women"
  },
  {
	"code": "1f46f-200d-2642",
	"name": "dancing_men"
  },
  {
	"code": "1f46b",
	"name": "couple"
  },
  {
	"code": "1f46c",
	"name": "two_men_holding_hands"
  },
  {
	"code": "1f46d",
	"name": "two_women_holding_hands"
  },
  {
	"code": "1f647-200d-2640-fe0f",
	"name": "bowing_woman"
  },
  {
	"code": "1f647",
	"name": "bowing_man"
  },
  {
	"code": "1f926-200d-2642-fe0f",
	"name": "man_facepalming"
  },
  {
	"code": "1f926-200d-2640-fe0f",
	"name": "woman_facepalming"
  },
  {
	"code": "1f937-200d-2640-fe0f",
	"name": "woman_shrugging"
  },
  {
	"code": "1f937-200d-2642-fe0f",
	"name": "man_shrugging"
  },
  {
	"code": "1f481-200d-2640-fe0f",
	"name": "tipping_hand_woman"
  },
  {
	"code": "1f481-200d-2642-fe0f",
	"name": "tipping_hand_man"
  },
  {
	"code": "1f645-200d-2640-fe0f",
	"name": "no_good_woman"
  },
  {
	"code": "1f645-200d-2642-fe0f",
	"name": "no_good_man"
  },
  {
	"code": "1f646-200d-2640-fe0f",
	"name": "ok_woman"
  },
  {
	"code": "1f646-200d-2642-fe0f",
	"name": "ok_man"
  },
  {
	"code": "1f64b-200d-2640-fe0f",
	"name": "raising_hand_woman"
  },
  {
	"code": "1f64b-200d-2642-fe0f",
	"name": "raising_hand_man"
  },
  {
	"code": "1f64e-200d-2640-fe0f",
	"name": "pouting_woman"
  },
  {
	"code": "1f64e-200d-2642-fe0f",
	"name": "pouting_man"
  },
  {
	"code": "1f64d-200d-2640-fe0f",
	"name": "frowning_woman"
  },
  {
	"code": "1f64d-200d-2642-fe0f",
	"name": "frowning_man"
  },
  {
	"code": "1f487-200d-2640-fe0f",
	"name": "haircut_woman"
  },
  {
	"code": "1f487-200d-2642-fe0f",
	"name": "haircut_man"
  },
  {
	"code": "1f486-200d-2640-fe0f",
	"name": "massage_woman"
  },
  {
	"code": "1f486-200d-2642-fe0f",
	"name": "massage_man"
  },
  {
	"code": "1f491",
	"name": "couple_with_heart"
  },
  {
	"code": "1f469-200d-2764-fe0f-200d-1f469",
	"name": "couple_with_heart_woman_woman"
  },
  {
	"code": "1f468-200d-2764-fe0f-200d-1f468",
	"name": "couple_with_heart_man_man"
  },
  {
	"code": "1f48f",
	"name": "couplekiss_man_woman"
  },
  {
	"code": "1f469-200d-2764-fe0f-200d-1f48b-200d-1f469",
	"name": "couplekiss_woman_woman"
  },
  {
	"code": "1f468-200d-2764-fe0f-200d-1f48b-200d-1f468",
	"name": "couplekiss_man_man"
  },
  {
	"code": "1f46a",
	"name": "family"
  },
  {
	"code": "1f468-200d-1f469-200d-1f467",
	"name": "family_man_woman_girl"
  },
  {
	"code": "1f468-200d-1f469-200d-1f467-200d-1f466",
	"name": "family_man_woman_girl_boy"
  },
  {
	"code": "1f468-200d-1f469-200d-1f466-200d-1f466",
	"name": "family_man_woman_boy_boy"
  },
  {
	"code": "1f468-200d-1f469-200d-1f467-200d-1f467",
	"name": "family_man_woman_girl_girl"
  },
  {
	"code": "1f469-200d-1f469-200d-1f466",
	"name": "family_woman_woman_boy"
  },
  {
	"code": "1f469-200d-1f469-200d-1f467",
	"name": "family_woman_woman_girl"
  },
  {
	"code": "1f469-200d-1f469-200d-1f467-200d-1f466",
	"name": "family_woman_woman_girl_boy"
  },
  {
	"code": "1f469-200d-1f469-200d-1f466-200d-1f466",
	"name": "family_woman_woman_boy_boy"
  },
  {
	"code": "1f469-200d-1f469-200d-1f467-200d-1f467",
	"name": "family_woman_woman_girl_girl"
  },
  {
	"code": "1f468-200d-1f468-200d-1f466",
	"name": "family_man_man_boy"
  },
  {
	"code": "1f468-200d-1f468-200d-1f467",
	"name": "family_man_man_girl"
  },
  {
	"code": "1f468-200d-1f468-200d-1f467-200d-1f466",
	"name": "family_man_man_girl_boy"
  },
  {
	"code": "1f468-200d-1f468-200d-1f466-200d-1f466",
	"name": "family_man_man_boy_boy"
  },
  {
	"code": "1f468-200d-1f468-200d-1f467-200d-1f467",
	"name": "family_man_man_girl_girl"
  },
  {
	"code": "1f469-200d-1f466",
	"name": "family_woman_boy"
  },
  {
	"code": "1f469-200d-1f467",
	"name": "family_woman_girl"
  },
  {
	"code": "1f469-200d-1f467-200d-1f466",
	"name": "family_woman_girl_boy"
  },
  {
	"code": "1f469-200d-1f466-200d-1f466",
	"name": "family_woman_boy_boy"
  },
  {
	"code": "1f469-200d-1f467-200d-1f467",
	"name": "family_woman_girl_girl"
  },
  {
	"code": "1f468-200d-1f466",
	"name": "family_man_boy"
  },
  {
	"code": "1f468-200d-1f467",
	"name": "family_man_girl"
  },
  {
	"code": "1f468-200d-1f467-200d-1f466",
	"name": "family_man_girl_boy"
  },
  {
	"code": "1f468-200d-1f466-200d-1f466",
	"name": "family_man_boy_boy"
  },
  {
	"code": "1f468-200d-1f467-200d-1f467",
	"name": "family_man_girl_girl"
  },
  {
	"code": "1f45a",
	"name": "womans_clothes"
  },
  {
	"code": "1f455",
	"name": "tshirt"
  },
  {
	"code": "1f456",
	"name": "jeans"
  },
  {
	"code": "1f454",
	"name": "necktie"
  },
  {
	"code": "1f457",
	"name": "dress"
  },
  {
	"code": "1f459",
	"name": "bikini"
  },
  {
	"code": "1f458",
	"name": "kimono"
  },
  {
	"code": "1f484",
	"name": "lipstick"
  },
  {
	"code": "1f48b",
	"name": "kiss"
  },
  {
	"code": "1f463",
	"name": "footprints"
  },
  {
	"code": "1f460",
	"name": "high_heel"
  },
  {
	"code": "1f461",
	"name": "sandal"
  },
  {
	"code": "1f462",
	"name": "boot"
  },
  {
	"code": "1f45e",
	"name": "mans_shoe"
  },
  {
	"code": "1f45f",
	"name": "athletic_shoe"
  },
  {
	"code": "1f452",
	"name": "womans_hat"
  },
  {
	"code": "1f3a9",
	"name": "tophat"
  },
  {
	"code": "26d1",
	"name": "rescue_worker_helmet"
  },
  {
	"code": "1f393",
	"name": "mortar_board"
  },
  {
	"code": "1f451",
	"name": "crown"
  },
  {
	"code": "1f392",
	"name": "school_satchel"
  },
  {
	"code": "1f45d",
	"name": "pouch"
  },
  {
	"code": "1f45b",
	"name": "purse"
  },
  {
	"code": "1f45c",
	"name": "handbag"
  },
  {
	"code": "1f4bc",
	"name": "briefcase"
  },
  {
	"code": "1f453",
	"name": "eyeglasses"
  },
  {
	"code": "1f576",
	"name": "dark_sunglasses"
  },
  {
	"code": "1f48d",
	"name": "ring"
  },
  {
	"code": "1f302",
	"name": "closed_umbrella"
  },
  {
	"code": "1f436",
	"name": "dog"
  },
  {
	"code": "1f431",
	"name": "cat"
  },
  {
	"code": "1f42d",
	"name": "mouse"
  },
  {
	"code": "1f439",
	"name": "hamster"
  },
  {
	"code": "1f430",
	"name": "rabbit"
  },
  {
	"code": "1f98a",
	"name": "fox_face"
  },
  {
	"code": "1f43b",
	"name": "bear"
  },
  {
	"code": "1f43c",
	"name": "panda_face"
  },
  {
	"code": "1f428",
	"name": "koala"
  },
  {
	"code": "1f42f",
	"name": "tiger"
  },
  {
	"code": "1f981",
	"name": "lion"
  },
  {
	"code": "1f42e",
	"name": "cow"
  },
  {
	"code": "1f437",
	"name": "pig"
  },
  {
	"code": "1f43d",
	"name": "pig_nose"
  },
  {
	"code": "1f438",
	"name": "frog"
  },
  {
	"code": "1f991",
	"name": "squid"
  },
  {
	"code": "1f419",
	"name": "octopus"
  },
  {
	"code": "1f990",
	"name": "shrimp"
  },
  {
	"code": "1f435",
	"name": "monkey_face"
  },
  {
	"code": "1f98d",
	"name": "gorilla"
  },
  {
	"code": "1f648",
	"name": "see_no_evil"
  },
  {
	"code": "1f649",
	"name": "hear_no_evil"
  },
  {
	"code": "1f64a",
	"name": "speak_no_evil"
  },
  {
	"code": "1f412",
	"name": "monkey"
  },
  {
	"code": "1f414",
	"name": "chicken"
  },
  {
	"code": "1f427",
	"name": "penguin"
  },
  {
	"code": "1f426",
	"name": "bird"
  },
  {
	"code": "1f424",
	"name": "baby_chick"
  },
  {
	"code": "1f423",
	"name": "hatching_chick"
  },
  {
	"code": "1f425",
	"name": "hatched_chick"
  },
  {
	"code": "1f986",
	"name": "duck"
  },
  {
	"code": "1f985",
	"name": "eagle"
  },
  {
	"code": "1f989",
	"name": "owl"
  },
  {
	"code": "1f987",
	"name": "bat"
  },
  {
	"code": "1f43a",
	"name": "wolf"
  },
  {
	"code": "1f417",
	"name": "boar"
  },
  {
	"code": "1f434",
	"name": "horse"
  },
  {
	"code": "1f984",
	"name": "unicorn"
  },
  {
	"code": "1f41d",
	"name": "honeybee"
  },
  {
	"code": "1f41b",
	"name": "bug"
  },
  {
	"code": "1f98b",
	"name": "butterfly"
  },
  {
	"code": "1f40c",
	"name": "snail"
  },
  {
	"code": "1f41e",
	"name": "lady_beetle"
  },
  {
	"code": "1f41c",
	"name": "ant"
  },
  {
	"code": "1f577",
	"name": "spider"
  },
  {
	"code": "1f982",
	"name": "scorpion"
  },
  {
	"code": "1f980",
	"name": "crab"
  },
  {
	"code": "1f40d",
	"name": "snake"
  },
  {
	"code": "1f98e",
	"name": "lizard"
  },
  {
	"code": "1f422",
	"name": "turtle"
  },
  {
	"code": "1f420",
	"name": "tropical_fish"
  },
  {
	"code": "1f41f",
	"name": "fish"
  },
  {
	"code": "1f421",
	"name": "blowfish"
  },
  {
	"code": "1f42c",
	"name": "dolphin"
  },
  {
	"code": "1f988",
	"name": "shark"
  },
  {
	"code": "1f433",
	"name": "whale"
  },
  {
	"code": "1f40b",
	"name": "whale2"
  },
  {
	"code": "1f40a",
	"name": "crocodile"
  },
  {
	"code": "1f406",
	"name": "leopard"
  },
  {
	"code": "1f405",
	"name": "tiger2"
  },
  {
	"code": "1f403",
	"name": "water_buffalo"
  },
  {
	"code": "1f402",
	"name": "ox"
  },
  {
	"code": "1f404",
	"name": "cow2"
  },
  {
	"code": "1f98c",
	"name": "deer"
  },
  {
	"code": "1f42a",
	"name": "dromedary_camel"
  },
  {
	"code": "1f42b",
	"name": "camel"
  },
  {
	"code": "1f418",
	"name": "elephant"
  },
  {
	"code": "1f98f",
	"name": "rhinoceros"
  },
  {
	"code": "1f410",
	"name": "goat"
  },
  {
	"code": "1f40f",
	"name": "ram"
  },
  {
	"code": "1f411",
	"name": "sheep"
  },
  {
	"code": "1f40e",
	"name": "racehorse"
  },
  {
	"code": "1f416",
	"name": "pig2"
  },
  {
	"code": "1f400",
	"name": "rat"
  },
  {
	"code": "1f401",
	"name": "mouse2"
  },
  {
	"code": "1f413",
	"name": "rooster"
  },
  {
	"code": "1f983",
	"name": "turkey"
  },
  {
	"code": "1f54a",
	"name": "dove"
  },
  {
	"code": "1f415",
	"name": "dog2"
  },
  {
	"code": "1f429",
	"name": "poodle"
  },
  {
	"code": "1f408",
	"name": "cat2"
  },
  {
	"code": "1f407",
	"name": "rabbit2"
  },
  {
	"code": "1f43f",
	"name": "chipmunk"
  },
  {
	"code": "1f43e",
	"name": "paw_prints"
  },
  {
	"code": "1f409",
	"name": "dragon"
  },
  {
	"code": "1f432",
	"name": "dragon_face"
  },
  {
	"code": "1f335",
	"name": "cactus"
  },
  {
	"code": "1f384",
	"name": "christmas_tree"
  },
  {
	"code": "1f332",
	"name": "evergreen_tree"
  },
  {
	"code": "1f333",
	"name": "deciduous_tree"
  },
  {
	"code": "1f334",
	"name": "palm_tree"
  },
  {
	"code": "1f331",
	"name": "seedling"
  },
  {
	"code": "1f33f",
	"name": "herb"
  },
  {
	"code": "2618",
	"name": "shamrock"
  },
  {
	"code": "1f340",
	"name": "four_leaf_clover"
  },
  {
	"code": "1f38d",
	"name": "bamboo"
  },
  {
	"code": "1f38b",
	"name": "tanabata_tree"
  },
  {
	"code": "1f343",
	"name": "leaves"
  },
  {
	"code": "1f342",
	"name": "fallen_leaf"
  },
  {
	"code": "1f341",
	"name": "maple_leaf"
  },
  {
	"code": "1f33e",
	"name": "ear_of_rice"
  },
  {
	"code": "1f33a",
	"name": "hibiscus"
  },
  {
	"code": "1f33b",
	"name": "sunflower"
  },
  {
	"code": "1f339",
	"name": "rose"
  },
  {
	"code": "1f940",
	"name": "wilted_flower"
  },
  {
	"code": "1f337",
	"name": "tulip"
  },
  {
	"code": "1f33c",
	"name": "blossom"
  },
  {
	"code": "1f338",
	"name": "cherry_blossom"
  },
  {
	"code": "1f490",
	"name": "bouquet"
  },
  {
	"code": "1f344",
	"name": "mushroom"
  },
  {
	"code": "1f330",
	"name": "chestnut"
  },
  {
	"code": "1f383",
	"name": "jack_o_lantern"
  },
  {
	"code": "1f41a",
	"name": "shell"
  },
  {
	"code": "1f578",
	"name": "spider_web"
  },
  {
	"code": "1f30e",
	"name": "earth_americas"
  },
  {
	"code": "1f30d",
	"name": "earth_africa"
  },
  {
	"code": "1f30f",
	"name": "earth_asia"
  },
  {
	"code": "1f315",
	"name": "full_moon"
  },
  {
	"code": "1f316",
	"name": "waning_gibbous_moon"
  },
  {
	"code": "1f317",
	"name": "last_quarter_moon"
  },
  {
	"code": "1f318",
	"name": "waning_crescent_moon"
  },
  {
	"code": "1f311",
	"name": "new_moon"
  },
  {
	"code": "1f312",
	"name": "waxing_crescent_moon"
  },
  {
	"code": "1f313",
	"name": "first_quarter_moon"
  },
  {
	"code": "1f314",
	"name": "waxing_gibbous_moon"
  },
  {
	"code": "1f31a",
	"name": "new_moon_with_face"
  },
  {
	"code": "1f31d",
	"name": "full_moon_with_face"
  },
  {
	"code": "1f31b",
	"name": "first_quarter_moon_with_face"
  },
  {
	"code": "1f31c",
	"name": "last_quarter_moon_with_face"
  },
  {
	"code": "1f31e",
	"name": "sun_with_face"
  },
  {
	"code": "1f319",
	"name": "crescent_moon"
  },
  {
	"code": "2b50",
	"name": "star"
  },
  {
	"code": "1f31f",
	"name": "star2"
  },
  {
	"code": "1f4ab",
	"name": "dizzy"
  },
  {
	"code": "2728",
	"name": "sparkles"
  },
  {
	"code": "2604",
	"name": "comet"
  },
  {
	"code": "2600",
	"name": "sunny"
  },
  {
	"code": "1f324",
	"name": "sun_behind_small_cloud"
  },
  {
	"code": "26c5",
	"name": "partly_sunny"
  },
  {
	"code": "1f325",
	"name": "sun_behind_large_cloud"
  },
  {
	"code": "1f326",
	"name": "sun_behind_rain_cloud"
  },
  {
	"code": "2601",
	"name": "cloud"
  },
  {
	"code": "1f327",
	"name": "cloud_with_rain"
  },
  {
	"code": "26c8",
	"name": "cloud_with_lightning_and_rain"
  },
  {
	"code": "1f329",
	"name": "cloud_with_lightning"
  },
  {
	"code": "26a1",
	"name": "zap"
  },
  {
	"code": "1f525",
	"name": "fire"
  },
  {
	"code": "1f4a5",
	"name": "boom"
  },
  {
	"code": "2744",
	"name": "snowflake"
  },
  {
	"code": "1f328",
	"name": "cloud_with_snow"
  },
  {
	"code": "26c4",
	"name": "snowman"
  },
  {
	"code": "2603",
	"name": "snowman_with_snow"
  },
  {
	"code": "1f32c",
	"name": "wind_face"
  },
  {
	"code": "1f4a8",
	"name": "dash"
  },
  {
	"code": "1f32a",
	"name": "tornado"
  },
  {
	"code": "1f32b",
	"name": "fog"
  },
  {
	"code": "2602",
	"name": "open_umbrella"
  },
  {
	"code": "2614",
	"name": "umbrella"
  },
  {
	"code": "1f4a7",
	"name": "droplet"
  },
  {
	"code": "1f4a6",
	"name": "sweat_drops"
  },
  {
	"code": "1f30a",
	"name": "ocean"
  },
  {
	"code": "1f34f",
	"name": "green_apple"
  },
  {
	"code": "1f34e",
	"name": "apple"
  },
  {
	"code": "1f350",
	"name": "pear"
  },
  {
	"code": "1f34a",
	"name": "tangerine"
  },
  {
	"code": "1f34b",
	"name": "lemon"
  },
  {
	"code": "1f34c",
	"name": "banana"
  },
  {
	"code": "1f349",
	"name": "watermelon"
  },
  {
	"code": "1f347",
	"name": "grapes"
  },
  {
	"code": "1f353",
	"name": "strawberry"
  },
  {
	"code": "1f348",
	"name": "melon"
  },
  {
	"code": "1f352",
	"name": "cherries"
  },
  {
	"code": "1f351",
	"name": "peach"
  },
  {
	"code": "1f34d",
	"name": "pineapple"
  },
  {
	"code": "1f95d",
	"name": "kiwi_fruit"
  },
  {
	"code": "1f951",
	"name": "avocado"
  },
  {
	"code": "1f345",
	"name": "tomato"
  },
  {
	"code": "1f346",
	"name": "eggplant"
  },
  {
	"code": "1f952",
	"name": "cucumber"
  },
  {
	"code": "1f955",
	"name": "carrot"
  },
  {
	"code": "1f336",
	"name": "hot_pepper"
  },
  {
	"code": "1f954",
	"name": "potato"
  },
  {
	"code": "1f33d",
	"name": "corn"
  },
  {
	"code": "1f360",
	"name": "sweet_potato"
  },
  {
	"code": "1f95c",
	"name": "peanuts"
  },
  {
	"code": "1f36f",
	"name": "honey_pot"
  },
  {
	"code": "1f950",
	"name": "croissant"
  },
  {
	"code": "1f35e",
	"name": "bread"
  },
  {
	"code": "1f956",
	"name": "baguette_bread"
  },
  {
	"code": "1f9c0",
	"name": "cheese"
  },
  {
	"code": "1f95a",
	"name": "egg"
  },
  {
	"code": "1f953",
	"name": "bacon"
  },
  {
	"code": "1f95e",
	"name": "pancakes"
  },
  {
	"code": "1f357",
	"name": "poultry_leg"
  },
  {
	"code": "1f356",
	"name": "meat_on_bone"
  },
  {
	"code": "1f364",
	"name": "fried_shrimp"
  },
  {
	"code": "1f373",
	"name": "fried_egg"
  },
  {
	"code": "1f354",
	"name": "hamburger"
  },
  {
	"code": "1f35f",
	"name": "fries"
  },
  {
	"code": "1f959",
	"name": "stuffed_flatbread"
  },
  {
	"code": "1f32d",
	"name": "hotdog"
  },
  {
	"code": "1f355",
	"name": "pizza"
  },
  {
	"code": "1f35d",
	"name": "spaghetti"
  },
  {
	"code": "1f32e",
	"name": "taco"
  },
  {
	"code": "1f32f",
	"name": "burrito"
  },
  {
	"code": "1f957",
	"name": "green_salad"
  },
  {
	"code": "1f958",
	"name": "shallow_pan_of_food"
  },
  {
	"code": "1f35c",
	"name": "ramen"
  },
  {
	"code": "1f372",
	"name": "stew"
  },
  {
	"code": "1f365",
	"name": "fish_cake"
  },
  {
	"code": "1f363",
	"name": "sushi"
  },
  {
	"code": "1f371",
	"name": "bento"
  },
  {
	"code": "1f35b",
	"name": "curry"
  },
  {
	"code": "1f359",
	"name": "rice_ball"
  },
  {
	"code": "1f35a",
	"name": "rice"
  },
  {
	"code": "1f358",
	"name": "rice_cracker"
  },
  {
	"code": "1f362",
	"name": "oden"
  },
  {
	"code": "1f361",
	"name": "dango"
  },
  {
	"code": "1f367",
	"name": "shaved_ice"
  },
  {
	"code": "1f368",
	"name": "ice_cream"
  },
  {
	"code": "1f366",
	"name": "icecream"
  },
  {
	"code": "1f370",
	"name": "cake"
  },
  {
	"code": "1f382",
	"name": "birthday"
  },
  {
	"code": "1f36e",
	"name": "custard"
  },
  {
	"code": "1f36c",
	"name": "candy"
  },
  {
	"code": "1f36d",
	"name": "lollipop"
  },
  {
	"code": "1f36b",
	"name": "chocolate_bar"
  },
  {
	"code": "1f37f",
	"name": "popcorn"
  },
  {
	"code": "1f369",
	"name": "doughnut"
  },
  {
	"code": "1f36a",
	"name": "cookie"
  },
  {
	"code": "1f95b",
	"name": "milk_glass"
  },
  {
	"code": "1f37a",
	"name": "beer"
  },
  {
	"code": "1f37b",
	"name": "beers"
  },
  {
	"code": "1f942",
	"name": "clinking_glasses"
  },
  {
	"code": "1f377",
	"name": "wine_glass"
  },
  {
	"code": "1f943",
	"name": "tumbler_glass"
  },
  {
	"code": "1f378",
	"name": "cocktail"
  },
  {
	"code": "1f379",
	"name": "tropical_drink"
  },
  {
	"code": "1f37e",
	"name": "champagne"
  },
  {
	"code": "1f376",
	"name": "sake"
  },
  {
	"code": "1f375",
	"name": "tea"
  },
  {
	"code": "2615",
	"name": "coffee"
  },
  {
	"code": "1f37c",
	"name": "baby_bottle"
  },
  {
	"code": "1f944",
	"name": "spoon"
  },
  {
	"code": "1f374",
	"name": "fork_and_knife"
  },
  {
	"code": "1f37d",
	"name": "plate_with_cutlery"
  },
  {
	"code": "26bd",
	"name": "soccer"
  },
  {
	"code": "1f3c0",
	"name": "basketball"
  },
  {
	"code": "1f3c8",
	"name": "football"
  },
  {
	"code": "26be",
	"name": "baseball"
  },
  {
	"code": "1f3be",
	"name": "tennis"
  },
  {
	"code": "1f3d0",
	"name": "volleyball"
  },
  {
	"code": "1f3c9",
	"name": "rugby_football"
  },
  {
	"code": "1f3b1",
	"name": "8ball"
  },
  {
	"code": "26f3",
	"name": "golf"
  },
  {
	"code": "1f3cc-fe0f-200d-2640",
	"name": "golfing_woman"
  },
  {
	"code": "1f3cc",
	"name": "golfing_man"
  },
  {
	"code": "1f3d3",
	"name": "ping_pong"
  },
  {
	"code": "1f3f8",
	"name": "badminton"
  },
  {
	"code": "1f945",
	"name": "goal_net"
  },
  {
	"code": "1f3d2",
	"name": "ice_hockey"
  },
  {
	"code": "1f3d1",
	"name": "field_hockey"
  },
  {
	"code": "1f3cf",
	"name": "cricket_bat_and_ball"
  },
  {
	"code": "1f3bf",
	"name": "ski"
  },
  {
	"code": "26f7",
	"name": "skier"
  },
  {
	"code": "1f3c2",
	"name": "snowboarder"
  },
  {
	"code": "1f93a",
	"name": "person_fencing"
  },
  {
	"code": "1f93c-200d-2640",
	"name": "women_wrestling"
  },
  {
	"code": "1f93c-200d-2642",
	"name": "men_wrestling"
  },
  {
	"code": "1f938-200d-2640-fe0f",
	"name": "woman_cartwheeling"
  },
  {
	"code": "1f938-200d-2642-fe0f",
	"name": "man_cartwheeling"
  },
  {
	"code": "1f93e-200d-2640-fe0f",
	"name": "woman_playing_handball"
  },
  {
	"code": "1f93e-200d-2642-fe0f",
	"name": "man_playing_handball"
  },
  {
	"code": "26f8",
	"name": "ice_skate"
  },
  {
	"code": "1f3f9",
	"name": "bow_and_arrow"
  },
  {
	"code": "1f3a3",
	"name": "fishing_pole_and_fish"
  },
  {
	"code": "1f94a",
	"name": "boxing_glove"
  },
  {
	"code": "1f94b",
	"name": "martial_arts_uniform"
  },
  {
	"code": "1f6a3-200d-2640-fe0f",
	"name": "rowing_woman"
  },
  {
	"code": "1f6a3",
	"name": "rowing_man"
  },
  {
	"code": "1f3ca-200d-2640-fe0f",
	"name": "swimming_woman"
  },
  {
	"code": "1f3ca",
	"name": "swimming_man"
  },
  {
	"code": "1f93d-200d-2640-fe0f",
	"name": "woman_playing_water_polo"
  },
  {
	"code": "1f93d-200d-2642-fe0f",
	"name": "man_playing_water_polo"
  },
  {
	"code": "1f3c4-200d-2640-fe0f",
	"name": "surfing_woman"
  },
  {
	"code": "1f3c4",
	"name": "surfing_man"
  },
  {
	"code": "1f6c0",
	"name": "bath"
  },
  {
	"code": "26f9-fe0f-200d-2640",
	"name": "basketball_woman"
  },
  {
	"code": "26f9",
	"name": "basketball_man"
  },
  {
	"code": "1f3cb-fe0f-200d-2640",
	"name": "weight_lifting_woman"
  },
  {
	"code": "1f3cb",
	"name": "weight_lifting_man"
  },
  {
	"code": "1f6b4-200d-2640-fe0f",
	"name": "biking_woman"
  },
  {
	"code": "1f6b4",
	"name": "biking_man"
  },
  {
	"code": "1f6b5-200d-2640-fe0f",
	"name": "mountain_biking_woman"
  },
  {
	"code": "1f6b5",
	"name": "mountain_biking_man"
  },
  {
	"code": "1f3c7",
	"name": "horse_racing"
  },
  {
	"code": "1f574",
	"name": "business_suit_levitating"
  },
  {
	"code": "1f3c6",
	"name": "trophy"
  },
  {
	"code": "1f3bd",
	"name": "running_shirt_with_sash"
  },
  {
	"code": "1f3c5",
	"name": "medal_sports"
  },
  {
	"code": "1f396",
	"name": "medal_military"
  },
  {
	"code": "1f947",
	"name": "1st_place_medal"
  },
  {
	"code": "1f948",
	"name": "2nd_place_medal"
  },
  {
	"code": "1f949",
	"name": "3rd_place_medal"
  },
  {
	"code": "1f397",
	"name": "reminder_ribbon"
  },
  {
	"code": "1f3f5",
	"name": "rosette"
  },
  {
	"code": "1f3ab",
	"name": "ticket"
  },
  {
	"code": "1f39f",
	"name": "tickets"
  },
  {
	"code": "1f3ad",
	"name": "performing_arts"
  },
  {
	"code": "1f3a8",
	"name": "art"
  },
  {
	"code": "1f3aa",
	"name": "circus_tent"
  },
  {
	"code": "1f939-200d-2640-fe0f",
	"name": "woman_juggling"
  },
  {
	"code": "1f939-200d-2642-fe0f",
	"name": "man_juggling"
  },
  {
	"code": "1f3a4",
	"name": "microphone"
  },
  {
	"code": "1f3a7",
	"name": "headphones"
  },
  {
	"code": "1f3bc",
	"name": "musical_score"
  },
  {
	"code": "1f3b9",
	"name": "musical_keyboard"
  },
  {
	"code": "1f941",
	"name": "drum"
  },
  {
	"code": "1f3b7",
	"name": "saxophone"
  },
  {
	"code": "1f3ba",
	"name": "trumpet"
  },
  {
	"code": "1f3b8",
	"name": "guitar"
  },
  {
	"code": "1f3bb",
	"name": "violin"
  },
  {
	"code": "1f3ac",
	"name": "clapper"
  },
  {
	"code": "1f3ae",
	"name": "video_game"
  },
  {
	"code": "1f47e",
	"name": "space_invader"
  },
  {
	"code": "1f3af",
	"name": "dart"
  },
  {
	"code": "1f3b2",
	"name": "game_die"
  },
  {
	"code": "1f3b0",
	"name": "slot_machine"
  },
  {
	"code": "1f3b3",
	"name": "bowling"
  },
  {
	"code": "1f697",
	"name": "red_car"
  },
  {
	"code": "1f695",
	"name": "taxi"
  },
  {
	"code": "1f699",
	"name": "blue_car"
  },
  {
	"code": "1f68c",
	"name": "bus"
  },
  {
	"code": "1f68e",
	"name": "trolleybus"
  },
  {
	"code": "1f3ce",
	"name": "racing_car"
  },
  {
	"code": "1f693",
	"name": "police_car"
  },
  {
	"code": "1f691",
	"name": "ambulance"
  },
  {
	"code": "1f692",
	"name": "fire_engine"
  },
  {
	"code": "1f690",
	"name": "minibus"
  },
  {
	"code": "1f69a",
	"name": "truck"
  },
  {
	"code": "1f69b",
	"name": "articulated_lorry"
  },
  {
	"code": "1f69c",
	"name": "tractor"
  },
  {
	"code": "1f6f4",
	"name": "kick_scooter"
  },
  {
	"code": "1f3cd",
	"name": "motorcycle"
  },
  {
	"code": "1f6b2",
	"name": "bike"
  },
  {
	"code": "1f6f5",
	"name": "motor_scooter"
  },
  {
	"code": "1f6a8",
	"name": "rotating_light"
  },
  {
	"code": "1f694",
	"name": "oncoming_police_car"
  },
  {
	"code": "1f68d",
	"name": "oncoming_bus"
  },
  {
	"code": "1f698",
	"name": "oncoming_automobile"
  },
  {
	"code": "1f696",
	"name": "oncoming_taxi"
  },
  {
	"code": "1f6a1",
	"name": "aerial_tramway"
  },
  {
	"code": "1f6a0",
	"name": "mountain_cableway"
  },
  {
	"code": "1f69f",
	"name": "suspension_railway"
  },
  {
	"code": "1f683",
	"name": "railway_car"
  },
  {
	"code": "1f68b",
	"name": "train"
  },
  {
	"code": "1f69d",
	"name": "monorail"
  },
  {
	"code": "1f684",
	"name": "bullettrain_side"
  },
  {
	"code": "1f685",
	"name": "bullettrain_front"
  },
  {
	"code": "1f688",
	"name": "light_rail"
  },
  {
	"code": "1f69e",
	"name": "mountain_railway"
  },
  {
	"code": "1f682",
	"name": "steam_locomotive"
  },
  {
	"code": "1f686",
	"name": "train2"
  },
  {
	"code": "1f687",
	"name": "metro"
  },
  {
	"code": "1f68a",
	"name": "tram"
  },
  {
	"code": "1f689",
	"name": "station"
  },
  {
	"code": "1f681",
	"name": "helicopter"
  },
  {
	"code": "1f6e9",
	"name": "small_airplane"
  },
  {
	"code": "2708",
	"name": "airplane"
  },
  {
	"code": "1f6eb",
	"name": "flight_departure"
  },
  {
	"code": "1f6ec",
	"name": "flight_arrival"
  },
  {
	"code": "26f5",
	"name": "sailboat"
  },
  {
	"code": "1f6e5",
	"name": "motor_boat"
  },
  {
	"code": "1f6a4",
	"name": "speedboat"
  },
  {
	"code": "26f4",
	"name": "ferry"
  },
  {
	"code": "1f6f3",
	"name": "passenger_ship"
  },
  {
	"code": "1f680",
	"name": "rocket"
  },
  {
	"code": "1f6f0",
	"name": "artificial_satellite"
  },
  {
	"code": "1f4ba",
	"name": "seat"
  },
  {
	"code": "1f6f6",
	"name": "canoe"
  },
  {
	"code": "2693",
	"name": "anchor"
  },
  {
	"code": "1f6a7",
	"name": "construction"
  },
  {
	"code": "26fd",
	"name": "fuelpump"
  },
  {
	"code": "1f68f",
	"name": "busstop"
  },
  {
	"code": "1f6a6",
	"name": "vertical_traffic_light"
  },
  {
	"code": "1f6a5",
	"name": "traffic_light"
  },
  {
	"code": "1f3c1",
	"name": "checkered_flag"
  },
  {
	"code": "1f6a2",
	"name": "ship"
  },
  {
	"code": "1f3a1",
	"name": "ferris_wheel"
  },
  {
	"code": "1f3a2",
	"name": "roller_coaster"
  },
  {
	"code": "1f3a0",
	"name": "carousel_horse"
  },
  {
	"code": "1f3d7",
	"name": "building_construction"
  },
  {
	"code": "1f301",
	"name": "foggy"
  },
  {
	"code": "1f5fc",
	"name": "tokyo_tower"
  },
  {
	"code": "1f3ed",
	"name": "factory"
  },
  {
	"code": "26f2",
	"name": "fountain"
  },
  {
	"code": "1f391",
	"name": "rice_scene"
  },
  {
	"code": "26f0",
	"name": "mountain"
  },
  {
	"code": "1f3d4",
	"name": "mountain_snow"
  },
  {
	"code": "1f5fb",
	"name": "mount_fuji"
  },
  {
	"code": "1f30b",
	"name": "volcano"
  },
  {
	"code": "1f5fe",
	"name": "japan"
  },
  {
	"code": "1f3d5",
	"name": "camping"
  },
  {
	"code": "26fa",
	"name": "tent"
  },
  {
	"code": "1f3de",
	"name": "national_park"
  },
  {
	"code": "1f6e3",
	"name": "motorway"
  },
  {
	"code": "1f6e4",
	"name": "railway_track"
  },
  {
	"code": "1f305",
	"name": "sunrise"
  },
  {
	"code": "1f304",
	"name": "sunrise_over_mountains"
  },
  {
	"code": "1f3dc",
	"name": "desert"
  },
  {
	"code": "1f3d6",
	"name": "beach_umbrella"
  },
  {
	"code": "1f3dd",
	"name": "desert_island"
  },
  {
	"code": "1f307",
	"name": "city_sunrise"
  },
  {
	"code": "1f306",
	"name": "city_sunset"
  },
  {
	"code": "1f3d9",
	"name": "cityscape"
  },
  {
	"code": "1f303",
	"name": "night_with_stars"
  },
  {
	"code": "1f309",
	"name": "bridge_at_night"
  },
  {
	"code": "1f30c",
	"name": "milky_way"
  },
  {
	"code": "1f320",
	"name": "stars"
  },
  {
	"code": "1f387",
	"name": "sparkler"
  },
  {
	"code": "1f386",
	"name": "fireworks"
  },
  {
	"code": "1f308",
	"name": "rainbow"
  },
  {
	"code": "1f3d8",
	"name": "houses"
  },
  {
	"code": "1f3f0",
	"name": "european_castle"
  },
  {
	"code": "1f3ef",
	"name": "japanese_castle"
  },
  {
	"code": "1f3df",
	"name": "stadium"
  },
  {
	"code": "1f5fd",
	"name": "statue_of_liberty"
  },
  {
	"code": "1f3e0",
	"name": "house"
  },
  {
	"code": "1f3e1",
	"name": "house_with_garden"
  },
  {
	"code": "1f3da",
	"name": "derelict_house"
  },
  {
	"code": "1f3e2",
	"name": "office"
  },
  {
	"code": "1f3ec",
	"name": "department_store"
  },
  {
	"code": "1f3e3",
	"name": "post_office"
  },
  {
	"code": "1f3e4",
	"name": "european_post_office"
  },
  {
	"code": "1f3e5",
	"name": "hospital"
  },
  {
	"code": "1f3e6",
	"name": "bank"
  },
  {
	"code": "1f3e8",
	"name": "hotel"
  },
  {
	"code": "1f3ea",
	"name": "convenience_store"
  },
  {
	"code": "1f3eb",
	"name": "school"
  },
  {
	"code": "1f3e9",
	"name": "love_hotel"
  },
  {
	"code": "1f492",
	"name": "wedding"
  },
  {
	"code": "1f3db",
	"name": "classical_building"
  },
  {
	"code": "26ea",
	"name": "church"
  },
  {
	"code": "1f54c",
	"name": "mosque"
  },
  {
	"code": "1f54d",
	"name": "synagogue"
  },
  {
	"code": "1f54b",
	"name": "kaaba"
  },
  {
	"code": "26e9",
	"name": "shinto_shrine"
  },
  {
	"code": "231a",
	"name": "watch"
  },
  {
	"code": "1f4f1",
	"name": "iphone"
  },
  {
	"code": "1f4f2",
	"name": "calling"
  },
  {
	"code": "1f4bb",
	"name": "computer"
  },
  {
	"code": "2328",
	"name": "keyboard"
  },
  {
	"code": "1f5a5",
	"name": "desktop_computer"
  },
  {
	"code": "1f5a8",
	"name": "printer"
  },
  {
	"code": "1f5b1",
	"name": "computer_mouse"
  },
  {
	"code": "1f5b2",
	"name": "trackball"
  },
  {
	"code": "1f579",
	"name": "joystick"
  },
  {
	"code": "1f5dc",
	"name": "clamp"
  },
  {
	"code": "1f4bd",
	"name": "minidisc"
  },
  {
	"code": "1f4be",
	"name": "floppy_disk"
  },
  {
	"code": "1f4bf",
	"name": "cd"
  },
  {
	"code": "1f4c0",
	"name": "dvd"
  },
  {
	"code": "1f4fc",
	"name": "vhs"
  },
  {
	"code": "1f4f7",
	"name": "camera"
  },
  {
	"code": "1f4f8",
	"name": "camera_flash"
  },
  {
	"code": "1f4f9",
	"name": "video_camera"
  },
  {
	"code": "1f3a5",
	"name": "movie_camera"
  },
  {
	"code": "1f4fd",
	"name": "film_projector"
  },
  {
	"code": "1f39e",
	"name": "film_strip"
  },
  {
	"code": "1f4de",
	"name": "telephone_receiver"
  },
  {
	"code": "260e",
	"name": "phone"
  },
  {
	"code": "1f4df",
	"name": "pager"
  },
  {
	"code": "1f4e0",
	"name": "fax"
  },
  {
	"code": "1f4fa",
	"name": "tv"
  },
  {
	"code": "1f4fb",
	"name": "radio"
  },
  {
	"code": "1f399",
	"name": "studio_microphone"
  },
  {
	"code": "1f39a",
	"name": "level_slider"
  },
  {
	"code": "1f39b",
	"name": "control_knobs"
  },
  {
	"code": "23f1",
	"name": "stopwatch"
  },
  {
	"code": "23f2",
	"name": "timer_clock"
  },
  {
	"code": "23f0",
	"name": "alarm_clock"
  },
  {
	"code": "1f570",
	"name": "mantelpiece_clock"
  },
  {
	"code": "23f3",
	"name": "hourglass_flowing_sand"
  },
  {
	"code": "231b",
	"name": "hourglass"
  },
  {
	"code": "1f4e1",
	"name": "satellite"
  },
  {
	"code": "1f50b",
	"name": "battery"
  },
  {
	"code": "1f50c",
	"name": "electric_plug"
  },
  {
	"code": "1f4a1",
	"name": "bulb"
  },
  {
	"code": "1f526",
	"name": "flashlight"
  },
  {
	"code": "1f56f",
	"name": "candle"
  },
  {
	"code": "1f5d1",
	"name": "wastebasket"
  },
  {
	"code": "1f6e2",
	"name": "oil_drum"
  },
  {
	"code": "1f4b8",
	"name": "money_with_wings"
  },
  {
	"code": "1f4b5",
	"name": "dollar"
  },
  {
	"code": "1f4b4",
	"name": "yen"
  },
  {
	"code": "1f4b6",
	"name": "euro"
  },
  {
	"code": "1f4b7",
	"name": "pound"
  },
  {
	"code": "1f4b0",
	"name": "moneybag"
  },
  {
	"code": "1f4b3",
	"name": "credit_card"
  },
  {
	"code": "1f48e",
	"name": "gem"
  },
  {
	"code": "2696",
	"name": "balance_scale"
  },
  {
	"code": "1f527",
	"name": "wrench"
  },
  {
	"code": "1f528",
	"name": "hammer"
  },
  {
	"code": "2692",
	"name": "hammer_and_pick"
  },
  {
	"code": "1f6e0",
	"name": "hammer_and_wrench"
  },
  {
	"code": "26cf",
	"name": "pick"
  },
  {
	"code": "1f529",
	"name": "nut_and_bolt"
  },
  {
	"code": "2699",
	"name": "gear"
  },
  {
	"code": "26d3",
	"name": "chains"
  },
  {
	"code": "1f52b",
	"name": "gun"
  },
  {
	"code": "1f4a3",
	"name": "bomb"
  },
  {
	"code": "1f52a",
	"name": "hocho"
  },
  {
	"code": "1f5e1",
	"name": "dagger"
  },
  {
	"code": "2694",
	"name": "crossed_swords"
  },
  {
	"code": "1f6e1",
	"name": "shield"
  },
  {
	"code": "1f6ac",
	"name": "smoking"
  },
  {
	"code": "2620",
	"name": "skull_and_crossbones"
  },
  {
	"code": "26b0",
	"name": "coffin"
  },
  {
	"code": "26b1",
	"name": "funeral_urn"
  },
  {
	"code": "1f3fa",
	"name": "amphora"
  },
  {
	"code": "1f52e",
	"name": "crystal_ball"
  },
  {
	"code": "1f4ff",
	"name": "prayer_beads"
  },
  {
	"code": "1f488",
	"name": "barber"
  },
  {
	"code": "2697",
	"name": "alembic"
  },
  {
	"code": "1f52d",
	"name": "telescope"
  },
  {
	"code": "1f52c",
	"name": "microscope"
  },
  {
	"code": "1f573",
	"name": "hole"
  },
  {
	"code": "1f48a",
	"name": "pill"
  },
  {
	"code": "1f489",
	"name": "syringe"
  },
  {
	"code": "1f321",
	"name": "thermometer"
  },
  {
	"code": "1f3f7",
	"name": "label"
  },
  {
	"code": "1f516",
	"name": "bookmark"
  },
  {
	"code": "1f6bd",
	"name": "toilet"
  },
  {
	"code": "1f6bf",
	"name": "shower"
  },
  {
	"code": "1f6c1",
	"name": "bathtub"
  },
  {
	"code": "1f511",
	"name": "key"
  },
  {
	"code": "1f5dd",
	"name": "old_key"
  },
  {
	"code": "1f6cb",
	"name": "couch_and_lamp"
  },
  {
	"code": "1f6cc",
	"name": "sleeping_bed"
  },
  {
	"code": "1f6cf",
	"name": "bed"
  },
  {
	"code": "1f6aa",
	"name": "door"
  },
  {
	"code": "1f6ce",
	"name": "bellhop_bell"
  },
  {
	"code": "1f5bc",
	"name": "framed_picture"
  },
  {
	"code": "1f5fa",
	"name": "world_map"
  },
  {
	"code": "26f1",
	"name": "parasol_on_ground"
  },
  {
	"code": "1f5ff",
	"name": "moyai"
  },
  {
	"code": "1f6cd",
	"name": "shopping"
  },
  {
	"code": "1f6d2",
	"name": "shopping_cart"
  },
  {
	"code": "1f388",
	"name": "balloon"
  },
  {
	"code": "1f38f",
	"name": "flags"
  },
  {
	"code": "1f380",
	"name": "ribbon"
  },
  {
	"code": "1f381",
	"name": "gift"
  },
  {
	"code": "1f38a",
	"name": "confetti_ball"
  },
  {
	"code": "1f389",
	"name": "tada"
  },
  {
	"code": "1f38e",
	"name": "dolls"
  },
  {
	"code": "1f390",
	"name": "wind_chime"
  },
  {
	"code": "1f38c",
	"name": "crossed_flags"
  },
  {
	"code": "1f3ee",
	"name": "izakaya_lantern"
  },
  {
	"code": "2709",
	"name": "email"
  },
  {
	"code": "1f4e9",
	"name": "envelope_with_arrow"
  },
  {
	"code": "1f4e8",
	"name": "incoming_envelope"
  },
  {
	"code": "1f4e7",
	"name": "e-mail"
  },
  {
	"code": "1f48c",
	"name": "love_letter"
  },
  {
	"code": "1f4ee",
	"name": "postbox"
  },
  {
	"code": "1f4ea",
	"name": "mailbox_closed"
  },
  {
	"code": "1f4eb",
	"name": "mailbox"
  },
  {
	"code": "1f4ec",
	"name": "mailbox_with_mail"
  },
  {
	"code": "1f4ed",
	"name": "mailbox_with_no_mail"
  },
  {
	"code": "1f4e6",
	"name": "package"
  },
  {
	"code": "1f4ef",
	"name": "postal_horn"
  },
  {
	"code": "1f4e5",
	"name": "inbox_tray"
  },
  {
	"code": "1f4e4",
	"name": "outbox_tray"
  },
  {
	"code": "1f4dc",
	"name": "scroll"
  },
  {
	"code": "1f4c3",
	"name": "page_with_curl"
  },
  {
	"code": "1f4d1",
	"name": "bookmark_tabs"
  },
  {
	"code": "1f4ca",
	"name": "bar_chart"
  },
  {
	"code": "1f4c8",
	"name": "chart_with_upwards_trend"
  },
  {
	"code": "1f4c9",
	"name": "chart_with_downwards_trend"
  },
  {
	"code": "1f4c4",
	"name": "page_facing_up"
  },
  {
	"code": "1f4c5",
	"name": "date"
  },
  {
	"code": "1f4c6",
	"name": "calendar"
  },
  {
	"code": "1f5d3",
	"name": "spiral_calendar"
  },
  {
	"code": "1f4c7",
	"name": "card_index"
  },
  {
	"code": "1f5c3",
	"name": "card_file_box"
  },
  {
	"code": "1f5f3",
	"name": "ballot_box"
  },
  {
	"code": "1f5c4",
	"name": "file_cabinet"
  },
  {
	"code": "1f4cb",
	"name": "clipboard"
  },
  {
	"code": "1f5d2",
	"name": "spiral_notepad"
  },
  {
	"code": "1f4c1",
	"name": "file_folder"
  },
  {
	"code": "1f4c2",
	"name": "open_file_folder"
  },
  {
	"code": "1f5c2",
	"name": "card_index_dividers"
  },
  {
	"code": "1f5de",
	"name": "newspaper_roll"
  },
  {
	"code": "1f4f0",
	"name": "newspaper"
  },
  {
	"code": "1f4d3",
	"name": "notebook"
  },
  {
	"code": "1f4d5",
	"name": "closed_book"
  },
  {
	"code": "1f4d7",
	"name": "green_book"
  },
  {
	"code": "1f4d8",
	"name": "blue_book"
  },
  {
	"code": "1f4d9",
	"name": "orange_book"
  },
  {
	"code": "1f4d4",
	"name": "notebook_with_decorative_cover"
  },
  {
	"code": "1f4d2",
	"name": "ledger"
  },
  {
	"code": "1f4da",
	"name": "books"
  },
  {
	"code": "1f4d6",
	"name": "open_book"
  },
  {
	"code": "1f517",
	"name": "link"
  },
  {
	"code": "1f4ce",
	"name": "paperclip"
  },
  {
	"code": "1f587",
	"name": "paperclips"
  },
  {
	"code": "2702",
	"name": "scissors"
  },
  {
	"code": "1f4d0",
	"name": "triangular_ruler"
  },
  {
	"code": "1f4cf",
	"name": "straight_ruler"
  },
  {
	"code": "1f4cc",
	"name": "pushpin"
  },
  {
	"code": "1f4cd",
	"name": "round_pushpin"
  },
  {
	"code": "1f6a9",
	"name": "triangular_flag_on_post"
  },
  {
	"code": "1f3f3",
	"name": "white_flag"
  },
  {
	"code": "1f3f4",
	"name": "black_flag"
  },
  {
	"code": "1f3f3-fe0f-200d-1f308",
	"name": "rainbow_flag"
  },
  {
	"code": "1f510",
	"name": "closed_lock_with_key"
  },
  {
	"code": "1f512",
	"name": "lock"
  },
  {
	"code": "1f513",
	"name": "unlock"
  },
  {
	"code": "1f50f",
	"name": "lock_with_ink_pen"
  },
  {
	"code": "1f58a",
	"name": "pen"
  },
  {
	"code": "1f58b",
	"name": "fountain_pen"
  },
  {
	"code": "2712",
	"name": "black_nib"
  },
  {
	"code": "1f4dd",
	"name": "memo"
  },
  {
	"code": "270f",
	"name": "pencil2"
  },
  {
	"code": "1f58d",
	"name": "crayon"
  },
  {
	"code": "1f58c",
	"name": "paintbrush"
  },
  {
	"code": "1f50d",
	"name": "mag"
  },
  {
	"code": "1f50e",
	"name": "mag_right"
  },
  {
	"code": "2764",
	"name": "heart"
  },
  {
	"code": "1f49b",
	"name": "yellow_heart"
  },
  {
	"code": "1f49a",
	"name": "green_heart"
  },
  {
	"code": "1f499",
	"name": "blue_heart"
  },
  {
	"code": "1f49c",
	"name": "purple_heart"
  },
  {
	"code": "1f5a4",
	"name": "black_heart"
  },
  {
	"code": "1f494",
	"name": "broken_heart"
  },
  {
	"code": "2763",
	"name": "heavy_heart_exclamation"
  },
  {
	"code": "1f495",
	"name": "two_hearts"
  },
  {
	"code": "1f49e",
	"name": "revolving_hearts"
  },
  {
	"code": "1f493",
	"name": "heartbeat"
  },
  {
	"code": "1f497",
	"name": "heartpulse"
  },
  {
	"code": "1f496",
	"name": "sparkling_heart"
  },
  {
	"code": "1f498",
	"name": "cupid"
  },
  {
	"code": "1f49d",
	"name": "gift_heart"
  },
  {
	"code": "1f49f",
	"name": "heart_decoration"
  },
  {
	"code": "262e",
	"name": "peace_symbol"
  },
  {
	"code": "271d",
	"name": "latin_cross"
  },
  {
	"code": "262a",
	"name": "star_and_crescent"
  },
  {
	"code": "1f549",
	"name": "om"
  },
  {
	"code": "2638",
	"name": "wheel_of_dharma"
  },
  {
	"code": "2721",
	"name": "star_of_david"
  },
  {
	"code": "1f52f",
	"name": "six_pointed_star"
  },
  {
	"code": "1f54e",
	"name": "menorah"
  },
  {
	"code": "262f",
	"name": "yin_yang"
  },
  {
	"code": "2626",
	"name": "orthodox_cross"
  },
  {
	"code": "1f6d0",
	"name": "place_of_worship"
  },
  {
	"code": "26ce",
	"name": "ophiuchus"
  },
  {
	"code": "2648",
	"name": "aries"
  },
  {
	"code": "2649",
	"name": "taurus"
  },
  {
	"code": "264a",
	"name": "gemini"
  },
  {
	"code": "264b",
	"name": "cancer"
  },
  {
	"code": "264c",
	"name": "leo"
  },
  {
	"code": "264d",
	"name": "virgo"
  },
  {
	"code": "264e",
	"name": "libra"
  },
  {
	"code": "264f",
	"name": "scorpius"
  },
  {
	"code": "2650",
	"name": "sagittarius"
  },
  {
	"code": "2651",
	"name": "capricorn"
  },
  {
	"code": "2652",
	"name": "aquarius"
  },
  {
	"code": "2653",
	"name": "pisces"
  },
  {
	"code": "1f194",
	"name": "id"
  },
  {
	"code": "269b",
	"name": "atom_symbol"
  },
  {
	"code": "1f233",
	"name": "u7a7a"
  },
  {
	"code": "1f239",
	"name": "u5272"
  },
  {
	"code": "2622",
	"name": "radioactive"
  },
  {
	"code": "2623",
	"name": "biohazard"
  },
  {
	"code": "1f4f4",
	"name": "mobile_phone_off"
  },
  {
	"code": "1f4f3",
	"name": "vibration_mode"
  },
  {
	"code": "1f236",
	"name": "u6709"
  },
  {
	"code": "1f21a",
	"name": "u7121"
  },
  {
	"code": "1f238",
	"name": "u7533"
  },
  {
	"code": "1f23a",
	"name": "u55b6"
  },
  {
	"code": "1f237",
	"name": "u6708"
  },
  {
	"code": "2734",
	"name": "eight_pointed_black_star"
  },
  {
	"code": "1f19a",
	"name": "vs"
  },
  {
	"code": "1f251",
	"name": "accept"
  },
  {
	"code": "1f4ae",
	"name": "white_flower"
  },
  {
	"code": "1f250",
	"name": "ideograph_advantage"
  },
  {
	"code": "3299",
	"name": "secret"
  },
  {
	"code": "3297",
	"name": "congratulations"
  },
  {
	"code": "1f234",
	"name": "u5408"
  },
  {
	"code": "1f235",
	"name": "u6e80"
  },
  {
	"code": "1f232",
	"name": "u7981"
  },
  {
	"code": "1f170",
	"name": "a"
  },
  {
	"code": "1f171",
	"name": "b"
  },
  {
	"code": "1f18e",
	"name": "ab"
  },
  {
	"code": "1f191",
	"name": "cl"
  },
  {
	"code": "1f17e",
	"name": "o2"
  },
  {
	"code": "1f198",
	"name": "sos"
  },
  {
	"code": "26d4",
	"name": "no_entry"
  },
  {
	"code": "1f4db",
	"name": "name_badge"
  },
  {
	"code": "1f6ab",
	"name": "no_entry_sign"
  },
  {
	"code": "274c",
	"name": "x"
  },
  {
	"code": "2b55",
	"name": "o"
  },
  {
	"code": "1f6d1",
	"name": "stop_sign"
  },
  {
	"code": "1f4a2",
	"name": "anger"
  },
  {
	"code": "2668",
	"name": "hotsprings"
  },
  {
	"code": "1f6b7",
	"name": "no_pedestrians"
  },
  {
	"code": "1f6af",
	"name": "do_not_litter"
  },
  {
	"code": "1f6b3",
	"name": "no_bicycles"
  },
  {
	"code": "1f6b1",
	"name": "non-potable_water"
  },
  {
	"code": "1f51e",
	"name": "underage"
  },
  {
	"code": "1f4f5",
	"name": "no_mobile_phones"
  },
  {
	"code": "2757",
	"name": "exclamation"
  },
  {
	"code": "2755",
	"name": "grey_exclamation"
  },
  {
	"code": "2753",
	"name": "question"
  },
  {
	"code": "2754",
	"name": "grey_question"
  },
  {
	"code": "203c",
	"name": "bangbang"
  },
  {
	"code": "2049",
	"name": "interrobang"
  },
  {
	"code": "1f4af",
	"name": "100"
  },
  {
	"code": "1f505",
	"name": "low_brightness"
  },
  {
	"code": "1f506",
	"name": "high_brightness"
  },
  {
	"code": "1f531",
	"name": "trident"
  },
  {
	"code": "269c",
	"name": "fleur_de_lis"
  },
  {
	"code": "303d",
	"name": "part_alternation_mark"
  },
  {
	"code": "26a0",
	"name": "warning"
  },
  {
	"code": "1f6b8",
	"name": "children_crossing"
  },
  {
	"code": "1f530",
	"name": "beginner"
  },
  {
	"code": "267b",
	"name": "recycle"
  },
  {
	"code": "1f22f",
	"name": "u6307"
  },
  {
	"code": "1f4b9",
	"name": "chart"
  },
  {
	"code": "2747",
	"name": "sparkle"
  },
  {
	"code": "2733",
	"name": "eight_spoked_asterisk"
  },
  {
	"code": "274e",
	"name": "negative_squared_cross_mark"
  },
  {
	"code": "2705",
	"name": "white_check_mark"
  },
  {
	"code": "1f4a0",
	"name": "diamond_shape_with_a_dot_inside"
  },
  {
	"code": "1f300",
	"name": "cyclone"
  },
  {
	"code": "27bf",
	"name": "loop"
  },
  {
	"code": "1f310",
	"name": "globe_with_meridians"
  },
  {
	"code": "24c2",
	"name": "m"
  },
  {
	"code": "1f3e7",
	"name": "atm"
  },
  {
	"code": "1f202",
	"name": "sa"
  },
  {
	"code": "1f6c2",
	"name": "passport_control"
  },
  {
	"code": "1f6c3",
	"name": "customs"
  },
  {
	"code": "1f6c4",
	"name": "baggage_claim"
  },
  {
	"code": "1f6c5",
	"name": "left_luggage"
  },
  {
	"code": "267f",
	"name": "wheelchair"
  },
  {
	"code": "1f6ad",
	"name": "no_smoking"
  },
  {
	"code": "1f6be",
	"name": "wc"
  },
  {
	"code": "1f17f",
	"name": "parking"
  },
  {
	"code": "1f6b0",
	"name": "potable_water"
  },
  {
	"code": "1f6b9",
	"name": "mens"
  },
  {
	"code": "1f6ba",
	"name": "womens"
  },
  {
	"code": "1f6bc",
	"name": "baby_symbol"
  },
  {
	"code": "1f6bb",
	"name": "restroom"
  },
  {
	"code": "1f6ae",
	"name": "put_litter_in_its_place"
  },
  {
	"code": "1f3a6",
	"name": "cinema"
  },
  {
	"code": "1f4f6",
	"name": "signal_strength"
  },
  {
	"code": "1f201",
	"name": "koko"
  },
  {
	"code": "1f196",
	"name": "ng"
  },
  {
	"code": "1f197",
	"name": "ok"
  },
  {
	"code": "1f199",
	"name": "up"
  },
  {
	"code": "1f192",
	"name": "cool"
  },
  {
	"code": "1f195",
	"name": "new"
  },
  {
	"code": "1f193",
	"name": "free"
  },
  {
	"code": "0030-fe0f-20e3",
	"name": "zero"
  },
  {
	"code": "0031-fe0f-20e3",
	"name": "one"
  },
  {
	"code": "0032-fe0f-20e3",
	"name": "two"
  },
  {
	"code": "0033-fe0f-20e3",
	"name": "three"
  },
  {
	"code": "0034-fe0f-20e3",
	"name": "four"
  },
  {
	"code": "0035-fe0f-20e3",
	"name": "five"
  },
  {
	"code": "0036-fe0f-20e3",
	"name": "six"
  },
  {
	"code": "0037-fe0f-20e3",
	"name": "seven"
  },
  {
	"code": "0038-fe0f-20e3",
	"name": "eight"
  },
  {
	"code": "0039-fe0f-20e3",
	"name": "nine"
  },
  {
	"code": "1f51f",
	"name": "keycap_ten"
  },
  {
	"code": "002a-fe0f-20e3",
	"name": "asterisk"
  },
  {
	"code": "1f522",
	"name": "1234"
  },
  {
	"code": "25b6",
	"name": "arrow_forward"
  },
  {
	"code": "23f8",
	"name": "pause_button"
  },
  {
	"code": "23ed",
	"name": "next_track_button"
  },
  {
	"code": "23f9",
	"name": "stop_button"
  },
  {
	"code": "23fa",
	"name": "record_button"
  },
  {
	"code": "23ef",
	"name": "play_or_pause_button"
  },
  {
	"code": "23ee",
	"name": "previous_track_button"
  },
  {
	"code": "23e9",
	"name": "fast_forward"
  },
  {
	"code": "23ea",
	"name": "rewind"
  },
  {
	"code": "1f500",
	"name": "twisted_rightwards_arrows"
  },
  {
	"code": "1f501",
	"name": "repeat"
  },
  {
	"code": "1f502",
	"name": "repeat_one"
  },
  {
	"code": "25c0",
	"name": "arrow_backward"
  },
  {
	"code": "1f53c",
	"name": "arrow_up_small"
  },
  {
	"code": "1f53d",
	"name": "arrow_down_small"
  },
  {
	"code": "23eb",
	"name": "arrow_double_up"
  },
  {
	"code": "23ec",
	"name": "arrow_double_down"
  },
  {
	"code": "27a1",
	"name": "arrow_right"
  },
  {
	"code": "2b05",
	"name": "arrow_left"
  },
  {
	"code": "2b06",
	"name": "arrow_up"
  },
  {
	"code": "2b07",
	"name": "arrow_down"
  },
  {
	"code": "2197",
	"name": "arrow_upper_right"
  },
  {
	"code": "2198",
	"name": "arrow_lower_right"
  },
  {
	"code": "2199",
	"name": "arrow_lower_left"
  },
  {
	"code": "2196",
	"name": "arrow_upper_left"
  },
  {
	"code": "2195",
	"name": "arrow_up_down"
  },
  {
	"code": "2194",
	"name": "left_right_arrow"
  },
  {
	"code": "1f504",
	"name": "arrows_counterclockwise"
  },
  {
	"code": "21aa",
	"name": "arrow_right_hook"
  },
  {
	"code": "21a9",
	"name": "leftwards_arrow_with_hook"
  },
  {
	"code": "2934",
	"name": "arrow_heading_up"
  },
  {
	"code": "2935",
	"name": "arrow_heading_down"
  },
  {
	"code": "0023-fe0f-20e3",
	"name": "hash"
  },
  {
	"code": "2139",
	"name": "information_source"
  },
  {
	"code": "1f524",
	"name": "abc"
  },
  {
	"code": "1f521",
	"name": "abcd"
  },
  {
	"code": "1f520",
	"name": "capital_abcd"
  },
  {
	"code": "1f523",
	"name": "symbols"
  },
  {
	"code": "1f3b5",
	"name": "musical_note"
  },
  {
	"code": "1f3b6",
	"name": "notes"
  },
  {
	"code": "3030",
	"name": "wavy_dash"
  },
  {
	"code": "27b0",
	"name": "curly_loop"
  },
  {
	"code": "2714",
	"name": "heavy_check_mark"
  },
  {
	"code": "1f503",
	"name": "arrows_clockwise"
  },
  {
	"code": "2795",
	"name": "heavy_plus_sign"
  },
  {
	"code": "2796",
	"name": "heavy_minus_sign"
  },
  {
	"code": "2797",
	"name": "heavy_division_sign"
  },
  {
	"code": "2716",
	"name": "heavy_multiplication_x"
  },
  {
	"code": "1f4b2",
	"name": "heavy_dollar_sign"
  },
  {
	"code": "1f4b1",
	"name": "currency_exchange"
  },
  {
	"code": "00a9",
	"name": "copyright"
  },
  {
	"code": "00ae",
	"name": "registered"
  },
  {
	"code": "2122",
	"name": "tm"
  },
  {
	"code": "1f51a",
	"name": "end"
  },
  {
	"code": "1f519",
	"name": "back"
  },
  {
	"code": "1f51b",
	"name": "on"
  },
  {
	"code": "1f51d",
	"name": "top"
  },
  {
	"code": "1f51c",
	"name": "soon"
  },
  {
	"code": "2611",
	"name": "ballot_box_with_check"
  },
  {
	"code": "1f518",
	"name": "radio_button"
  },
  {
	"code": "26aa",
	"name": "white_circle"
  },
  {
	"code": "26ab",
	"name": "black_circle"
  },
  {
	"code": "1f534",
	"name": "red_circle"
  },
  {
	"code": "1f535",
	"name": "large_blue_circle"
  },
  {
	"code": "1f538",
	"name": "small_orange_diamond"
  },
  {
	"code": "1f539",
	"name": "small_blue_diamond"
  },
  {
	"code": "1f536",
	"name": "large_orange_diamond"
  },
  {
	"code": "1f537",
	"name": "large_blue_diamond"
  },
  {
	"code": "1f53a",
	"name": "small_red_triangle"
  },
  {
	"code": "25aa",
	"name": "black_small_square"
  },
  {
	"code": "25ab",
	"name": "white_small_square"
  },
  {
	"code": "2b1b",
	"name": "black_large_square"
  },
  {
	"code": "2b1c",
	"name": "white_large_square"
  },
  {
	"code": "1f53b",
	"name": "small_red_triangle_down"
  },
  {
	"code": "25fc",
	"name": "black_medium_square"
  },
  {
	"code": "25fb",
	"name": "white_medium_square"
  },
  {
	"code": "25fe",
	"name": "black_medium_small_square"
  },
  {
	"code": "25fd",
	"name": "white_medium_small_square"
  },
  {
	"code": "1f532",
	"name": "black_square_button"
  },
  {
	"code": "1f533",
	"name": "white_square_button"
  },
  {
	"code": "1f508",
	"name": "speaker"
  },
  {
	"code": "1f509",
	"name": "sound"
  },
  {
	"code": "1f50a",
	"name": "loud_sound"
  },
  {
	"code": "1f507",
	"name": "mute"
  },
  {
	"code": "1f4e3",
	"name": "mega"
  },
  {
	"code": "1f4e2",
	"name": "loudspeaker"
  },
  {
	"code": "1f514",
	"name": "bell"
  },
  {
	"code": "1f515",
	"name": "no_bell"
  },
  {
	"code": "1f0cf",
	"name": "black_joker"
  },
  {
	"code": "1f004",
	"name": "mahjong"
  },
  {
	"code": "2660",
	"name": "spades"
  },
  {
	"code": "2663",
	"name": "clubs"
  },
  {
	"code": "2665",
	"name": "hearts"
  },
  {
	"code": "2666",
	"name": "diamonds"
  },
  {
	"code": "1f3b4",
	"name": "flower_playing_cards"
  },
  {
	"code": "1f4ad",
	"name": "thought_balloon"
  },
  {
	"code": "1f5ef",
	"name": "right_anger_bubble"
  },
  {
	"code": "1f4ac",
	"name": "speech_balloon"
  },
  {
	"code": "1f5e8",
	"name": "left_speech_bubble"
  },
  {
	"code": "1f550",
	"name": "clock1"
  },
  {
	"code": "1f551",
	"name": "clock2"
  },
  {
	"code": "1f552",
	"name": "clock3"
  },
  {
	"code": "1f553",
	"name": "clock4"
  },
  {
	"code": "1f554",
	"name": "clock5"
  },
  {
	"code": "1f555",
	"name": "clock6"
  },
  {
	"code": "1f556",
	"name": "clock7"
  },
  {
	"code": "1f557",
	"name": "clock8"
  },
  {
	"code": "1f558",
	"name": "clock9"
  },
  {
	"code": "1f559",
	"name": "clock10"
  },
  {
	"code": "1f55a",
	"name": "clock11"
  },
  {
	"code": "1f55b",
	"name": "clock12"
  },
  {
	"code": "1f55c",
	"name": "clock130"
  },
  {
	"code": "1f55d",
	"name": "clock230"
  },
  {
	"code": "1f55e",
	"name": "clock330"
  },
  {
	"code": "1f55f",
	"name": "clock430"
  },
  {
	"code": "1f560",
	"name": "clock530"
  },
  {
	"code": "1f561",
	"name": "clock630"
  },
  {
	"code": "1f562",
	"name": "clock730"
  },
  {
	"code": "1f563",
	"name": "clock830"
  },
  {
	"code": "1f564",
	"name": "clock930"
  },
  {
	"code": "1f565",
	"name": "clock1030"
  },
  {
	"code": "1f566",
	"name": "clock1130"
  },
  {
	"code": "1f567",
	"name": "clock1230"
  },
  {
	"code": "1f1e6-1f1eb",
	"name": "afghanistan"
  },
  {
	"code": "1f1e6-1f1fd",
	"name": "aland_islands"
  },
  {
	"code": "1f1e6-1f1f1",
	"name": "albania"
  },
  {
	"code": "1f1e9-1f1ff",
	"name": "algeria"
  },
  {
	"code": "1f1e6-1f1f8",
	"name": "american_samoa"
  },
  {
	"code": "1f1e6-1f1e9",
	"name": "andorra"
  },
  {
	"code": "1f1e6-1f1f4",
	"name": "angola"
  },
  {
	"code": "1f1e6-1f1ee",
	"name": "anguilla"
  },
  {
	"code": "1f1e6-1f1f6",
	"name": "antarctica"
  },
  {
	"code": "1f1e6-1f1ec",
	"name": "antigua_barbuda"
  },
  {
	"code": "1f1e6-1f1f7",
	"name": "argentina"
  },
  {
	"code": "1f1e6-1f1f2",
	"name": "armenia"
  },
  {
	"code": "1f1e6-1f1fc",
	"name": "aruba"
  },
  {
	"code": "1f1e6-1f1fa",
	"name": "australia"
  },
  {
	"code": "1f1e6-1f1f9",
	"name": "austria"
  },
  {
	"code": "1f1e6-1f1ff",
	"name": "azerbaijan"
  },
  {
	"code": "1f1e7-1f1f8",
	"name": "bahamas"
  },
  {
	"code": "1f1e7-1f1ed",
	"name": "bahrain"
  },
  {
	"code": "1f1e7-1f1e9",
	"name": "bangladesh"
  },
  {
	"code": "1f1e7-1f1e7",
	"name": "barbados"
  },
  {
	"code": "1f1e7-1f1fe",
	"name": "belarus"
  },
  {
	"code": "1f1e7-1f1ea",
	"name": "belgium"
  },
  {
	"code": "1f1e7-1f1ff",
	"name": "belize"
  },
  {
	"code": "1f1e7-1f1ef",
	"name": "benin"
  },
  {
	"code": "1f1e7-1f1f2",
	"name": "bermuda"
  },
  {
	"code": "1f1e7-1f1f9",
	"name": "bhutan"
  },
  {
	"code": "1f1e7-1f1f4",
	"name": "bolivia"
  },
  {
	"code": "1f1e7-1f1f6",
	"name": "caribbean_netherlands"
  },
  {
	"code": "1f1e7-1f1e6",
	"name": "bosnia_herzegovina"
  },
  {
	"code": "1f1e7-1f1fc",
	"name": "botswana"
  },
  {
	"code": "1f1e7-1f1f7",
	"name": "brazil"
  },
  {
	"code": "1f1ee-1f1f4",
	"name": "british_indian_ocean_territory"
  },
  {
	"code": "1f1fb-1f1ec",
	"name": "british_virgin_islands"
  },
  {
	"code": "1f1e7-1f1f3",
	"name": "brunei"
  },
  {
	"code": "1f1e7-1f1ec",
	"name": "bulgaria"
  },
  {
	"code": "1f1e7-1f1eb",
	"name": "burkina_faso"
  },
  {
	"code": "1f1e7-1f1ee",
	"name": "burundi"
  },
  {
	"code": "1f1e8-1f1fb",
	"name": "cape_verde"
  },
  {
	"code": "1f1f0-1f1ed",
	"name": "cambodia"
  },
  {
	"code": "1f1e8-1f1f2",
	"name": "cameroon"
  },
  {
	"code": "1f1e8-1f1e6",
	"name": "canada"
  },
  {
	"code": "1f1ee-1f1e8",
	"name": "canary_islands"
  },
  {
	"code": "1f1f0-1f1fe",
	"name": "cayman_islands"
  },
  {
	"code": "1f1e8-1f1eb",
	"name": "central_african_republic"
  },
  {
	"code": "1f1f9-1f1e9",
	"name": "chad"
  },
  {
	"code": "1f1e8-1f1f1",
	"name": "chile"
  },
  {
	"code": "1f1e8-1f1f3",
	"name": "cn"
  },
  {
	"code": "1f1e8-1f1fd",
	"name": "christmas_island"
  },
  {
	"code": "1f1e8-1f1e8",
	"name": "cocos_islands"
  },
  {
	"code": "1f1e8-1f1f4",
	"name": "colombia"
  },
  {
	"code": "1f1f0-1f1f2",
	"name": "comoros"
  },
  {
	"code": "1f1e8-1f1ec",
	"name": "congo_brazzaville"
  },
  {
	"code": "1f1e8-1f1e9",
	"name": "congo_kinshasa"
  },
  {
	"code": "1f1e8-1f1f0",
	"name": "cook_islands"
  },
  {
	"code": "1f1e8-1f1f7",
	"name": "costa_rica"
  },
  {
	"code": "1f1ed-1f1f7",
	"name": "croatia"
  },
  {
	"code": "1f1e8-1f1fa",
	"name": "cuba"
  },
  {
	"code": "1f1e8-1f1fc",
	"name": "curacao"
  },
  {
	"code": "1f1e8-1f1fe",
	"name": "cyprus"
  },
  {
	"code": "1f1e8-1f1ff",
	"name": "czech_republic"
  },
  {
	"code": "1f1e9-1f1f0",
	"name": "denmark"
  },
  {
	"code": "1f1e9-1f1ef",
	"name": "djibouti"
  },
  {
	"code": "1f1e9-1f1f2",
	"name": "dominica"
  },
  {
	"code": "1f1e9-1f1f4",
	"name": "dominican_republic"
  },
  {
	"code": "1f1ea-1f1e8",
	"name": "ecuador"
  },
  {
	"code": "1f1ea-1f1ec",
	"name": "egypt"
  },
  {
	"code": "1f1f8-1f1fb",
	"name": "el_salvador"
  },
  {
	"code": "1f1ec-1f1f6",
	"name": "equatorial_guinea"
  },
  {
	"code": "1f1ea-1f1f7",
	"name": "eritrea"
  },
  {
	"code": "1f1ea-1f1ea",
	"name": "estonia"
  },
  {
	"code": "1f1ea-1f1f9",
	"name": "ethiopia"
  },
  {
	"code": "1f1ea-1f1fa",
	"name": "eu"
  },
  {
	"code": "1f1eb-1f1f0",
	"name": "falkland_islands"
  },
  {
	"code": "1f1eb-1f1f4",
	"name": "faroe_islands"
  },
  {
	"code": "1f1eb-1f1ef",
	"name": "fiji"
  },
  {
	"code": "1f1eb-1f1ee",
	"name": "finland"
  },
  {
	"code": "1f1eb-1f1f7",
	"name": "fr"
  },
  {
	"code": "1f1ec-1f1eb",
	"name": "french_guiana"
  },
  {
	"code": "1f1f5-1f1eb",
	"name": "french_polynesia"
  },
  {
	"code": "1f1f9-1f1eb",
	"name": "french_southern_territories"
  },
  {
	"code": "1f1ec-1f1e6",
	"name": "gabon"
  },
  {
	"code": "1f1ec-1f1f2",
	"name": "gambia"
  },
  {
	"code": "1f1ec-1f1ea",
	"name": "georgia"
  },
  {
	"code": "1f1e9-1f1ea",
	"name": "de"
  },
  {
	"code": "1f1ec-1f1ed",
	"name": "ghana"
  },
  {
	"code": "1f1ec-1f1ee",
	"name": "gibraltar"
  },
  {
	"code": "1f1ec-1f1f7",
	"name": "greece"
  },
  {
	"code": "1f1ec-1f1f1",
	"name": "greenland"
  },
  {
	"code": "1f1ec-1f1e9",
	"name": "grenada"
  },
  {
	"code": "1f1ec-1f1f5",
	"name": "guadeloupe"
  },
  {
	"code": "1f1ec-1f1fa",
	"name": "guam"
  },
  {
	"code": "1f1ec-1f1f9",
	"name": "guatemala"
  },
  {
	"code": "1f1ec-1f1ec",
	"name": "guernsey"
  },
  {
	"code": "1f1ec-1f1f3",
	"name": "guinea"
  },
  {
	"code": "1f1ec-1f1fc",
	"name": "guinea_bissau"
  },
  {
	"code": "1f1ec-1f1fe",
	"name": "guyana"
  },
  {
	"code": "1f1ed-1f1f9",
	"name": "haiti"
  },
  {
	"code": "1f1ed-1f1f3",
	"name": "honduras"
  },
  {
	"code": "1f1ed-1f1f0",
	"name": "hong_kong"
  },
  {
	"code": "1f1ed-1f1fa",
	"name": "hungary"
  },
  {
	"code": "1f1ee-1f1f8",
	"name": "iceland"
  },
  {
	"code": "1f1ee-1f1f3",
	"name": "india"
  },
  {
	"code": "1f1ee-1f1e9",
	"name": "indonesia"
  },
  {
	"code": "1f1ee-1f1f7",
	"name": "iran"
  },
  {
	"code": "1f1ee-1f1f6",
	"name": "iraq"
  },
  {
	"code": "1f1ee-1f1ea",
	"name": "ireland"
  },
  {
	"code": "1f1ee-1f1f2",
	"name": "isle_of_man"
  },
  {
	"code": "1f1ee-1f1f1",
	"name": "israel"
  },
  {
	"code": "1f1ee-1f1f9",
	"name": "it"
  },
  {
	"code": "1f1e8-1f1ee",
	"name": "cote_divoire"
  },
  {
	"code": "1f1ef-1f1f2",
	"name": "jamaica"
  },
  {
	"code": "1f1ef-1f1f5",
	"name": "jp"
  },
  {
	"code": "1f1ef-1f1ea",
	"name": "jersey"
  },
  {
	"code": "1f1ef-1f1f4",
	"name": "jordan"
  },
  {
	"code": "1f1f0-1f1ff",
	"name": "kazakhstan"
  },
  {
	"code": "1f1f0-1f1ea",
	"name": "kenya"
  },
  {
	"code": "1f1f0-1f1ee",
	"name": "kiribati"
  },
  {
	"code": "1f1fd-1f1f0",
	"name": "kosovo"
  },
  {
	"code": "1f1f0-1f1fc",
	"name": "kuwait"
  },
  {
	"code": "1f1f0-1f1ec",
	"name": "kyrgyzstan"
  },
  {
	"code": "1f1f1-1f1e6",
	"name": "laos"
  },
  {
	"code": "1f1f1-1f1fb",
	"name": "latvia"
  },
  {
	"code": "1f1f1-1f1e7",
	"name": "lebanon"
  },
  {
	"code": "1f1f1-1f1f8",
	"name": "lesotho"
  },
  {
	"code": "1f1f1-1f1f7",
	"name": "liberia"
  },
  {
	"code": "1f1f1-1f1fe",
	"name": "libya"
  },
  {
	"code": "1f1f1-1f1ee",
	"name": "liechtenstein"
  },
  {
	"code": "1f1f1-1f1f9",
	"name": "lithuania"
  },
  {
	"code": "1f1f1-1f1fa",
	"name": "luxembourg"
  },
  {
	"code": "1f1f2-1f1f4",
	"name": "macau"
  },
  {
	"code": "1f1f2-1f1f0",
	"name": "macedonia"
  },
  {
	"code": "1f1f2-1f1ec",
	"name": "madagascar"
  },
  {
	"code": "1f1f2-1f1fc",
	"name": "malawi"
  },
  {
	"code": "1f1f2-1f1fe",
	"name": "malaysia"
  },
  {
	"code": "1f1f2-1f1fb",
	"name": "maldives"
  },
  {
	"code": "1f1f2-1f1f1",
	"name": "mali"
  },
  {
	"code": "1f1f2-1f1f9",
	"name": "malta"
  },
  {
	"code": "1f1f2-1f1ed",
	"name": "marshall_islands"
  },
  {
	"code": "1f1f2-1f1f6",
	"name": "martinique"
  },
  {
	"code": "1f1f2-1f1f7",
	"name": "mauritania"
  },
  {
	"code": "1f1f2-1f1fa",
	"name": "mauritius"
  },
  {
	"code": "1f1fe-1f1f9",
	"name": "mayotte"
  },
  {
	"code": "1f1f2-1f1fd",
	"name": "mexico"
  },
  {
	"code": "1f1eb-1f1f2",
	"name": "micronesia"
  },
  {
	"code": "1f1f2-1f1e9",
	"name": "moldova"
  },
  {
	"code": "1f1f2-1f1e8",
	"name": "monaco"
  },
  {
	"code": "1f1f2-1f1f3",
	"name": "mongolia"
  },
  {
	"code": "1f1f2-1f1ea",
	"name": "montenegro"
  },
  {
	"code": "1f1f2-1f1f8",
	"name": "montserrat"
  },
  {
	"code": "1f1f2-1f1e6",
	"name": "morocco"
  },
  {
	"code": "1f1f2-1f1ff",
	"name": "mozambique"
  },
  {
	"code": "1f1f2-1f1f2",
	"name": "myanmar"
  },
  {
	"code": "1f1f3-1f1e6",
	"name": "namibia"
  },
  {
	"code": "1f1f3-1f1f7",
	"name": "nauru"
  },
  {
	"code": "1f1f3-1f1f5",
	"name": "nepal"
  },
  {
	"code": "1f1f3-1f1f1",
	"name": "netherlands"
  },
  {
	"code": "1f1f3-1f1e8",
	"name": "new_caledonia"
  },
  {
	"code": "1f1f3-1f1ff",
	"name": "new_zealand"
  },
  {
	"code": "1f1f3-1f1ee",
	"name": "nicaragua"
  },
  {
	"code": "1f1f3-1f1ea",
	"name": "niger"
  },
  {
	"code": "1f1f3-1f1ec",
	"name": "nigeria"
  },
  {
	"code": "1f1f3-1f1fa",
	"name": "niue"
  },
  {
	"code": "1f1f3-1f1eb",
	"name": "norfolk_island"
  },
  {
	"code": "1f1f2-1f1f5",
	"name": "northern_mariana_islands"
  },
  {
	"code": "1f1f0-1f1f5",
	"name": "north_korea"
  },
  {
	"code": "1f1f3-1f1f4",
	"name": "norway"
  },
  {
	"code": "1f1f4-1f1f2",
	"name": "oman"
  },
  {
	"code": "1f1f5-1f1f0",
	"name": "pakistan"
  },
  {
	"code": "1f1f5-1f1fc",
	"name": "palau"
  },
  {
	"code": "1f1f5-1f1f8",
	"name": "palestinian_territories"
  },
  {
	"code": "1f1f5-1f1e6",
	"name": "panama"
  },
  {
	"code": "1f1f5-1f1ec",
	"name": "papua_new_guinea"
  },
  {
	"code": "1f1f5-1f1fe",
	"name": "paraguay"
  },
  {
	"code": "1f1f5-1f1ea",
	"name": "peru"
  },
  {
	"code": "1f1f5-1f1ed",
	"name": "philippines"
  },
  {
	"code": "1f1f5-1f1f3",
	"name": "pitcairn_islands"
  },
  {
	"code": "1f1f5-1f1f1",
	"name": "poland"
  },
  {
	"code": "1f1f5-1f1f9",
	"name": "portugal"
  },
  {
	"code": "1f1f5-1f1f7",
	"name": "puerto_rico"
  },
  {
	"code": "1f1f6-1f1e6",
	"name": "qatar"
  },
  {
	"code": "1f1f7-1f1ea",
	"name": "reunion"
  },
  {
	"code": "1f1f7-1f1f4",
	"name": "romania"
  },
  {
	"code": "1f1f7-1f1fa",
	"name": "ru"
  },
  {
	"code": "1f1f7-1f1fc",
	"name": "rwanda"
  },
  {
	"code": "1f1e7-1f1f1",
	"name": "st_barthelemy"
  },
  {
	"code": "1f1f8-1f1ed",
	"name": "st_helena"
  },
  {
	"code": "1f1f0-1f1f3",
	"name": "st_kitts_nevis"
  },
  {
	"code": "1f1f1-1f1e8",
	"name": "st_lucia"
  },
  {
	"code": "1f1f5-1f1f2",
	"name": "st_pierre_miquelon"
  },
  {
	"code": "1f1fb-1f1e8",
	"name": "st_vincent_grenadines"
  },
  {
	"code": "1f1fc-1f1f8",
	"name": "samoa"
  },
  {
	"code": "1f1f8-1f1f2",
	"name": "san_marino"
  },
  {
	"code": "1f1f8-1f1f9",
	"name": "sao_tome_principe"
  },
  {
	"code": "1f1f8-1f1e6",
	"name": "saudi_arabia"
  },
  {
	"code": "1f1f8-1f1f3",
	"name": "senegal"
  },
  {
	"code": "1f1f7-1f1f8",
	"name": "serbia"
  },
  {
	"code": "1f1f8-1f1e8",
	"name": "seychelles"
  },
  {
	"code": "1f1f8-1f1f1",
	"name": "sierra_leone"
  },
  {
	"code": "1f1f8-1f1ec",
	"name": "singapore"
  },
  {
	"code": "1f1f8-1f1fd",
	"name": "sint_maarten"
  },
  {
	"code": "1f1f8-1f1f0",
	"name": "slovakia"
  },
  {
	"code": "1f1f8-1f1ee",
	"name": "slovenia"
  },
  {
	"code": "1f1f8-1f1e7",
	"name": "solomon_islands"
  },
  {
	"code": "1f1f8-1f1f4",
	"name": "somalia"
  },
  {
	"code": "1f1ff-1f1e6",
	"name": "south_africa"
  },
  {
	"code": "1f1ec-1f1f8",
	"name": "south_georgia_south_sandwich_islands"
  },
  {
	"code": "1f1f0-1f1f7",
	"name": "kr"
  },
  {
	"code": "1f1f8-1f1f8",
	"name": "south_sudan"
  },
  {
	"code": "1f1ea-1f1f8",
	"name": "es"
  },
  {
	"code": "1f1f1-1f1f0",
	"name": "sri_lanka"
  },
  {
	"code": "1f1f8-1f1e9",
	"name": "sudan"
  },
  {
	"code": "1f1f8-1f1f7",
	"name": "suriname"
  },
  {
	"code": "1f1f8-1f1ff",
	"name": "swaziland"
  },
  {
	"code": "1f1f8-1f1ea",
	"name": "sweden"
  },
  {
	"code": "1f1e8-1f1ed",
	"name": "switzerland"
  },
  {
	"code": "1f1f8-1f1fe",
	"name": "syria"
  },
  {
	"code": "1f1f9-1f1fc",
	"name": "taiwan"
  },
  {
	"code": "1f1f9-1f1ef",
	"name": "tajikistan"
  },
  {
	"code": "1f1f9-1f1ff",
	"name": "tanzania"
  },
  {
	"code": "1f1f9-1f1ed",
	"name": "thailand"
  },
  {
	"code": "1f1f9-1f1f1",
	"name": "timor_leste"
  },
  {
	"code": "1f1f9-1f1ec",
	"name": "togo"
  },
  {
	"code": "1f1f9-1f1f0",
	"name": "tokelau"
  },
  {
	"code": "1f1f9-1f1f4",
	"name": "tonga"
  },
  {
	"code": "1f1f9-1f1f9",
	"name": "trinidad_tobago"
  },
  {
	"code": "1f1f9-1f1f3",
	"name": "tunisia"
  },
  {
	"code": "1f1f9-1f1f7",
	"name": "tr"
  },
  {
	"code": "1f1f9-1f1f2",
	"name": "turkmenistan"
  },
  {
	"code": "1f1f9-1f1e8",
	"name": "turks_caicos_islands"
  },
  {
	"code": "1f1f9-1f1fb",
	"name": "tuvalu"
  },
  {
	"code": "1f1fa-1f1ec",
	"name": "uganda"
  },
  {
	"code": "1f1fa-1f1e6",
	"name": "ukraine"
  },
  {
	"code": "1f1e6-1f1ea",
	"name": "united_arab_emirates"
  },
  {
	"code": "1f1ec-1f1e7",
	"name": "uk"
  },
  {
	"code": "1f1fa-1f1f8",
	"name": "us"
  },
  {
	"code": "1f1fb-1f1ee",
	"name": "us_virgin_islands"
  },
  {
	"code": "1f1fa-1f1fe",
	"name": "uruguay"
  },
  {
	"code": "1f1fa-1f1ff",
	"name": "uzbekistan"
  },
  {
	"code": "1f1fb-1f1fa",
	"name": "vanuatu"
  },
  {
	"code": "1f1fb-1f1e6",
	"name": "vatican_city"
  },
  {
	"code": "1f1fb-1f1ea",
	"name": "venezuela"
  },
  {
	"code": "1f1fb-1f1f3",
	"name": "vietnam"
  },
  {
	"code": "1f1fc-1f1eb",
	"name": "wallis_futuna"
  },
  {
	"code": "1f1ea-1f1ed",
	"name": "western_sahara"
  },
  {
	"code": "1f1fe-1f1ea",
	"name": "yemen"
  },
  {
	"code": "1f1ff-1f1f2",
	"name": "zambia"
  },
  {
	"code": "1f1ff-1f1fc",
	"name": "zimbabwe"
  },
  {
	"code": "1f929",
	"name": "star_struck"
  },
  {
	"code": "1f928",
	"name": "face_with_raised_eyebrow"
  },
  {
	"code": "1f92f",
	"name": "exploding_head"
  },
  {
	"code": "1f92a",
	"name": "crazy_face"
  },
  {
	"code": "1f92c",
	"name": "face_with_symbols_over_mouth"
  },
  {
	"code": "1f92e",
	"name": "face_vomiting"
  },
  {
	"code": "1f92b",
	"name": "shushing_face"
  },
  {
	"code": "1f92d",
	"name": "face_with_hand_over_mouth"
  },
  {
	"code": "1f9d0",
	"name": "face_with_monocle"
  },
  {
	"code": "1f9d2",
	"name": "child"
  },
  {
	"code": "1f9d1",
	"name": "adult"
  },
  {
	"code": "1f9d3",
	"name": "older_adult"
  },
  {
	"code": "1f9d5",
	"name": "woman_with_headscarf"
  },
  {
	"code": "1f9d4",
	"name": "bearded_person"
  },
  {
	"code": "1f931",
	"name": "breast_feeding"
  },
  {
	"code": "1f9d9",
	"name": "mage"
  },
  {
	"code": "1f9d9-200d-2640-fe0f",
	"name": "woman_mage"
  },
  {
	"code": "1f9da",
	"name": "fairy"
  },
  {
	"code": "1f9db",
	"name": "vampire"
  },
  {
	"code": "1f9dc",
	"name": "merperson"
  },
  {
	"code": "1f9dc-200d-2642-fe0f",
	"name": "merman"
  },
  {
	"code": "1f9dd",
	"name": "elf"
  },
  {
	"code": "1f9de",
	"name": "genie"
  },
  {
	"code": "1f9de-200d-2640",
	"name": "woman_genie"
  },
  {
	"code": "1f9df",
	"name": "zombie"
  },
  {
	"code": "1f9df-200d-2640",
	"name": "woman_zombie"
  },
  {
	"code": "1f9d6",
	"name": "person_in_steamy_room"
  },
  {
	"code": "1f9d6-200d-2640-fe0f",
	"name": "woman_in_steamy_room"
  },
  {
	"code": "1f9d7",
	"name": "person_climbing"
  },
  {
	"code": "1f9d7-200d-2640-fe0f",
	"name": "woman_climbing"
  },
  {
	"code": "1f9d8",
	"name": "person_in_lotus_position"
  },
  {
	"code": "1f9d8-200d-2640-fe0f",
	"name": "woman_in_lotus_position"
  },
  {
	"code": "1f91f",
	"name": "love_you_gesture"
  },
  {
	"code": "1f932",
	"name": "palms_up_together"
  },
  {
	"code": "1f9e0",
	"name": "brain"
  },
  {
	"code": "1f9e1",
	"name": "orange_heart"
  },
  {
	"code": "1f9e3",
	"name": "scarf"
  },
  {
	"code": "1f9e4",
	"name": "gloves"
  },
  {
	"code": "1f9e5",
	"name": "coat"
  },
  {
	"code": "1f9e6",
	"name": "socks"
  },
  {
	"code": "1f9e2",
	"name": "billed_cap"
  },
  {
	"code": "1f993",
	"name": "zebra"
  },
  {
	"code": "1f992",
	"name": "giraffe"
  },
  {
	"code": "1f994",
	"name": "hedgehog"
  },
  {
	"code": "1f995",
	"name": "sauropod"
  },
  {
	"code": "1f996",
	"name": "t_rex"
  },
  {
	"code": "1f997",
	"name": "cricket"
  },
  {
	"code": "1f965",
	"name": "coconut"
  },
  {
	"code": "1f966",
	"name": "broccoli"
  },
  {
	"code": "1f968",
	"name": "pretzel"
  },
  {
	"code": "1f969",
	"name": "cut_of_meat"
  },
  {
	"code": "1f96a",
	"name": "sandwich"
  },
  {
	"code": "1f963",
	"name": "bowl_with_spoon"
  },
  {
	"code": "1f96b",
	"name": "canned_food"
  },
  {
	"code": "1f95f",
	"name": "dumpling"
  },
  {
	"code": "1f960",
	"name": "fortune_cookie"
  },
  {
	"code": "1f961",
	"name": "takeout_box"
  },
  {
	"code": "1f967",
	"name": "pie"
  },
  {
	"code": "1f964",
	"name": "cup_with_straw"
  },
  {
	"code": "1f962",
	"name": "chopsticks"
  },
  {
	"code": "1f6f8",
	"name": "flying_saucer"
  },
  {
	"code": "1f6f7",
	"name": "sled"
  },
  {
	"code": "1f94c",
	"name": "curling_stone"
  },
  {
	"code": "1f1f8-1f1ef",
	"name": "svalbard_and_jan_mayen"
  },
  {
	"code": "1f1f2-1f1eb",
	"name": "st_martin"
  },
  {
	"code": "1f1fa-1f1f2",
	"name": "us_outlying_islands"
  },
  {
	"code": "1f1f9-1f1e6",
	"name": "tristan_da_cunha"
  },
  {
	"code": "1f1ed-1f1f2",
	"name": "heard_and_mc_donald_islands"
  },
  {
	"code": "1f1ea-1f1e6",
	"name": "ceuta_and_melilla"
  },
  {
	"code": "1f1e9-1f1ec",
	"name": "diego_garcia"
  },
  {
	"code": "1f1e6-1f1e8",
	"name": "ascension_island"
  },
  {
	"code": "1f1e7-1f1fb",
	"name": "bouvet_island"
  },
  {
	"code": "1f1e8-1f1f5",
	"name": "clipperton_island"
  },
  {
	"code": "1f1fa-1f1f3",
	"name": "united_nations"
  },
  {
	"code": "1f970",
	"name": "smiling_face_with_three_hearts"
  },
  {
	"code": "1f975",
	"name": "hot_face"
  },
  {
	"code": "1f976",
	"name": "cold_face"
  },
  {
	"code": "1f973",
	"name": "partying_face"
  },
  {
	"code": "1f974",
	"name": "woozy_face"
  },
  {
	"code": "1f97a",
	"name": "pleading_face"
  },
  {
	"code": "1f468-200d-1f9b0",
	"name": "man_red_haired"
  },
  {
	"code": "1f468-200d-1f9b1",
	"name": "man_curly_haired"
  },
  {
	"code": "1f468-200d-1f9b3",
	"name": "man_white_haired"
  },
  {
	"code": "1f468-200d-1f9b2",
	"name": "man_bald"
  },
  {
	"code": "1f469-200d-1f9b0",
	"name": "woman_red_haired"
  },
  {
	"code": "1f469-200d-1f9b1",
	"name": "woman_curly_haired"
  },
  {
	"code": "1f469-200d-1f9b3",
	"name": "woman_white_haired"
  },
  {
	"code": "1f469-200d-1f9b2",
	"name": "woman_bald"
  },
  {
	"code": "1f9b8",
	"name": "superhero"
  },
  {
	"code": "1f9b8-200d-2642-fe0f",
	"name": "man_superhero"
  },
  {
	"code": "1f9b8-200d-2640-fe0f",
	"name": "woman_superhero"
  },
  {
	"code": "1f9b9",
	"name": "supervillain"
  },
  {
	"code": "1f9b9-200d-2640-fe0f",
	"name": "woman_supervillain"
  },
  {
	"code": "1f9b9-200d-2642-fe0f",
	"name": "man_supervillain"
  },
  {
	"code": "1f9b5",
	"name": "leg"
  },
  {
	"code": "1f9b6",
	"name": "foot"
  },
  {
	"code": "1f9b4",
	"name": "bone"
  },
  {
	"code": "1f9b7",
	"name": "tooth"
  },
  {
	"code": "1f97d",
	"name": "goggles"
  },
  {
	"code": "1f97c",
	"name": "lab_coat"
  },
  {
	"code": "1f97e",
	"name": "hiking_boot"
  },
  {
	"code": "1f97f",
	"name": "flat_shoe"
  },
  {
	"code": "1f99d",
	"name": "raccoon"
  },
  {
	"code": "1f999",
	"name": "llama"
  },
  {
	"code": "1f99b",
	"name": "hippopotamus"
  },
  {
	"code": "1f998",
	"name": "kangaroo"
  },
  {
	"code": "1f9a1",
	"name": "badger"
  },
  {
	"code": "1f9a2",
	"name": "swan"
  },
  {
	"code": "1f99a",
	"name": "peacock"
  },
  {
	"code": "1f99c",
	"name": "parrot"
  },
  {
	"code": "1f99e",
	"name": "lobster"
  },
  {
	"code": "1f99f",
	"name": "mosquito"
  },
  {
	"code": "1f9a0",
	"name": "microbe"
  },
  {
	"code": "1f96d",
	"name": "mango"
  },
  {
	"code": "1f96c",
	"name": "leafy_green"
  },
  {
	"code": "1f96f",
	"name": "bagel"
  },
  {
	"code": "1f9c2",
	"name": "salt"
  },
  {
	"code": "1f96e",
	"name": "moon_cake"
  },
  {
	"code": "1f9c1",
	"name": "cupcake"
  },
  {
	"code": "1f9ed",
	"name": "compass"
  },
  {
	"code": "1f9f1",
	"name": "brick"
  },
  {
	"code": "1f6f9",
	"name": "skateboard"
  },
  {
	"code": "1f9f3",
	"name": "luggage"
  },
  {
	"code": "1f9e8",
	"name": "firecracker"
  },
  {
	"code": "1f9e7",
	"name": "red_gift_envelope"
  },
  {
	"code": "1f94e",
	"name": "softball"
  },
  {
	"code": "1f94f",
	"name": "flying_disc"
  },
  {
	"code": "1f94d",
	"name": "lacrosse"
  },
  {
	"code": "1f9ff",
	"name": "nazar_amulet"
  },
  {
	"code": "1f9e9",
	"name": "jigsaw"
  },
  {
	"code": "1f9f8",
	"name": "teddy_bear"
  },
  {
	"code": "265f",
	"name": "chess_pawn"
  },
  {
	"code": "1f9f5",
	"name": "thread"
  },
  {
	"code": "1f9f6",
	"name": "yarn"
  },
  {
	"code": "1f9ee",
	"name": "abacus"
  },
  {
	"code": "1f9fe",
	"name": "receipt"
  },
  {
	"code": "1f9f0",
	"name": "toolbox"
  },
  {
	"code": "1f9f2",
	"name": "magnet"
  },
  {
	"code": "1f9ea",
	"name": "test_tube"
  },
  {
	"code": "1f9eb",
	"name": "petri_dish"
  },
  {
	"code": "1f9ec",
	"name": "dna"
  },
  {
	"code": "1f9f4",
	"name": "lotion_bottle"
  },
  {
	"code": "1f9f7",
	"name": "safety_pin"
  },
  {
	"code": "1f9f9",
	"name": "broom"
  },
  {
	"code": "1f9fa",
	"name": "basket"
  },
  {
	"code": "1f9fb",
	"name": "roll_of_toilet_paper"
  },
  {
	"code": "1f9fc",
	"name": "soap"
  },
  {
	"code": "1f9fd",
	"name": "sponge"
  },
  {
	"code": "1f9ef",
	"name": "fire_extinguisher"
  },
  {
	"code": "267e",
	"name": "infinity"
  },
  {
	"code": "1f3f4-200d-2620",
	"name": "pirate_flag"
  },
  {
	"code": "1f9c7",
	"name": "waffle"
  },
  {
	"code": "1f9a6",
	"name": "otter"
  },
  {
	"code": "1f9a5",
	"name": "sloth"
  },
  {
	"code": "1f9ca",
	"name": "ice_cube"
  },
  {
	"code": "1fa90",
	"name": "ringer_planet"
  },
  {
	"code": "1f9a9",
	"name": "flamingo"
  },
  {
	"code": "1f971",
	"name": "yawning_face"
  },
  {
	"code": "1f90f",
	"name": "pinching_hand"
  },
  {
	"code": "1f415-200d-1f9ba",
	"name": "service_dog"
  },
  {
	"code": "1f9a7",
	"name": "orangutan"
  },
  {
	"code": "1f6fa",
	"name": "auto_rickshaw"
  },
  {
	"code": "1fa82",
	"name": "parachute"
  },
  {
	"code": "1fa80",
	"name": "yo-yo"
  },
  {
	"code": "1fa81",
	"name": "kite"
  },
  {
	"code": "1f7eb",
	"name": "brown_square"
  },
  {
	"code": "1f7ea",
	"name": "purple_square"
  },
  {
	"code": "1f7e6",
	"name": "blue_square"
  },
  {
	"code": "1f7e9",
	"name": "green_square"
  },
  {
	"code": "1f7e8",
	"name": "yellow_square"
  },
  {
	"code": "1f7e7",
	"name": "orange_square"
  },
  {
	"code": "1f7e5",
	"name": "red_square"
  },
  {
	"code": "1f7e4",
	"name": "brown_circle"
  },
  {
	"code": "1f7e3",
	"name": "purple_circle"
  },
  {
	"code": "1f7e2",
	"name": "green_circle"
  },
  {
	"code": "1f7e1",
	"name": "yellow_circle"
  },
  {
	"code": "1f7e0",
	"name": "orange_circle"
  },
  {
	"code": "1fa92",
	"name": "razor"
  },
  {
	"code": "1fa91",
	"name": "chair"
  },
  {
	"code": "1fa7a",
	"name": "stethoscope"
  },
  {
	"code": "1fa79",
	"name": "adhesive_bandage"
  },
  {
	"code": "1fa78",
	"name": "drop_of_blood"
  },
  {
	"code": "1f9af",
	"name": "probing_cane"
  },
  {
	"code": "1fa93",
	"name": "axe"
  },
  {
	"code": "1fa94",
	"name": "diya_lamp"
  },
  {
	"code": "1fa95",
	"name": "banjo"
  },
  {
	"code": "1fa70",
	"name": "ballet_shoes"
  },
  {
	"code": "1fa73",
	"name": "shorts"
  },
  {
	"code": "1fa72",
	"name": "briefs"
  },
  {
	"code": "1fa71",
	"name": "one_piece_swimsuit"
  },
  {
	"code": "1f97b",
	"name": "sari"
  },
  {
	"code": "1f9ba",
	"name": "safety_vest"
  },
  {
	"code": "1f93f",
	"name": "diving_mask"
  },
  {
	"code": "1f9bc",
	"name": "motorized_wheelchair"
  },
  {
	"code": "1f9bd",
	"name": "manual_wheelchair"
  },
  {
	"code": "1f6d5",
	"name": "hindu_temple"
  },
  {
	"code": "1f9c9",
	"name": "maté"
  },
  {
	"code": "1f9c3",
	"name": "beverage_box"
  },
  {
	"code": "1f9aa",
	"name": "oyster"
  },
  {
	"code": "1f9c8",
	"name": "butter"
  },
  {
	"code": "1f9c6",
	"name": "falafel"
  },
  {
	"code": "1f9c5",
	"name": "onion"
  },
  {
	"code": "1f9c4",
	"name": "garlic"
  },
  {
	"code": "1f9a8",
	"name": "skunk"
  },
  {
	"code": "1f9ae",
	"name": "guide_dog"
  },
  {
	"code": "1f9d1-200d-1f91d-200d-1f9d1",
	"name": "people_holding_hands"
  },
  {
	"code": "1f469-200d-1f9bd",
	"name": "woman_in_manual_wheelchair"
  },
  {
	"code": "1f468-200d-1f9bd",
	"name": "man_in_manual_wheelchair"
  },
  {
	"code": "1f469-200d-1f9bc",
	"name": "woman_in_motorized_wheelchair"
  },
  {
	"code": "1f468-200d-1f9bc",
	"name": "man_in_motorized_wheelchair"
  },
  {
	"code": "1f469-200d-1f9af",
	"name": "woman_with_probing_cane"
  },
  {
	"code": "1f468-200d-1f9af",
	"name": "man_with_probing_cane"
  },
  {
	"code": "1f9ce-200d-2640-fe0f",
	"name": "woman_kneeling"
  },
  {
	"code": "1f9ce-200d-2642-fe0f",
	"name": "man_kneeling"
  },
  {
	"code": "1f9cd-200d-2642-fe0f",
	"name": "man_standing"
  },
  {
	"code": "1f9cd-200d-2640-fe0f",
	"name": "woman_standing"
  },
  {
	"code": "1f9cf-200d-2640-fe0f",
	"name": "deaf_woman"
  },
  {
	"code": "1f9cf-200d-2642-fe0f",
	"name": "deaf_man"
  },
  {
	"code": "1f9bb",
	"name": "hear_with_hearing_aid"
  },
  {
	"code": "1f9bf",
	"name": "mechanical_leg"
  },
  {
	"code": "1f9be",
	"name": "mechanical_arm"
  },
  {
	"code": "1f90d",
	"name": "white_heart"
  },
  {
	"code": "1f90e",
	"name": "brown_heart"
  },
  {
	"code": "1f3f3-fe0f-200d-26a7",
	"name": "transgender_flag"
  },
  {
	"code": "1f972",
	"name": "smiling_face_with_tear"
  },
  {
	"code": "1f978",
	"name": "disguised_face"
  },
  {
	"code": "1f90c",
	"name": "pinched_fingers"
  },
  {
	"code": "1fac0",
	"name": "anatomical_heart"
  },
  {
	"code": "1fac1",
	"name": "lungs"
  },
  {
	"code": "1f977",
	"name": "ninja"
  },
  {
	"code": "1f9d1-200d-1f384",
	"name": "mx_claus"
  },
  {
	"code": "1fac2",
	"name": "people_hugging"
  },
  {
	"code": "1f408-200d-2b1b",
	"name": "black_cat"
  },
  {
	"code": "1f9ac",
	"name": "bison"
  },
  {
	"code": "1f9a3",
	"name": "mammoth"
  },
  {
	"code": "1f9ab",
	"name": "beaver"
  },
  {
	"code": "1f9a4",
	"name": "dodo"
  },
  {
	"code": "1fab6",
	"name": "feather"
  },
  {
	"code": "1f9ad",
	"name": "seal"
  },
  {
	"code": "1fab2",
	"name": "beetle"
  },
  {
	"code": "1fab3",
	"name": "cockroach"
  },
  {
	"code": "1fab0",
	"name": "fly"
  },
  {
	"code": "1fab1",
	"name": "worm"
  },
  {
	"code": "1fab4",
	"name": "potted_plant"
  },
  {
	"code": "1fad0",
	"name": "blueberries"
  },
  {
	"code": "1fad2",
	"name": "olive"
  },
  {
	"code": "1fad1",
	"name": "bell_pepper"
  },
  {
	"code": "1fad3",
	"name": "flatbread"
  },
  {
	"code": "1fad4",
	"name": "tamale"
  },
  {
	"code": "1fad5",
	"name": "fondue"
  },
  {
	"code": "1fad6",
	"name": "teapot"
  },
  {
	"code": "1f9cb",
	"name": "bubble_tea"
  },
  {
	"code": "1faa8",
	"name": "rock"
  },
  {
	"code": "1fab5",
	"name": "wood"
  },
  {
	"code": "1f6d6",
	"name": "hut"
  },
  {
	"code": "1f6fb",
	"name": "pickup_truck"
  },
  {
	"code": "1f6fc",
	"name": "roller_skate"
  },
  {
	"code": "1fa84",
	"name": "magic_wand"
  },
  {
	"code": "1fa85",
	"name": "piñata"
  },
  {
	"code": "1fa86",
	"name": "nesting_dolls"
  },
  {
	"code": "1faa1",
	"name": "sewing_needle"
  },
  {
	"code": "1faa2",
	"name": "knot"
  },
  {
	"code": "1fa74",
	"name": "thong_sandal"
  },
  {
	"code": "1fa96",
	"name": "military_helmet"
  },
  {
	"code": "1fa97",
	"name": "accordion"
  },
  {
	"code": "1fa98",
	"name": "long_drum"
  },
  {
	"code": "1fa99",
	"name": "coin"
  },
  {
	"code": "1fa83",
	"name": "boomerang"
  },
  {
	"code": "1fa9a",
	"name": "carpentry_saw"
  },
  {
	"code": "1fa9b",
	"name": "screwdriver"
  },
  {
	"code": "1fa9d",
	"name": "hook"
  },
  {
	"code": "1fa9c",
	"name": "ladder"
  },
  {
	"code": "1fa9e",
	"name": "mirror"
  },
  {
	"code": "1fa9f",
	"name": "window"
  },
  {
	"code": "1faa0",
	"name": "plunger"
  },
  {
	"code": "1faa4",
	"name": "mouse_trap"
  },
  {
	"code": "1faa3",
	"name": "bucket"
  },
  {
	"code": "1faa5",
	"name": "toothbrush"
  },
  {
	"code": "1faa6",
	"name": "headstone"
  },
  {
	"code": "1faa7",
	"name": "placard"
  },
  {
	"code": "26a7",
	"name": "transgender_symbol"
  },
  {
	"code": "1f468-200d-1f37c",
	"name": "man_feeding_baby"
  },
  {
	"code": "1f9d1-200d-1f37c",
	"name": "person_feeding_baby"
  },
  {
	"code": "1f43b-200d-2744",
	"name": "polar_bear"
  },
  {
	"code": "1fae0",
	"name": "melting_face"
  },
  {
	"code": "263a",
	"name": "smiling_face"
  },
  {
	"code": "1fae2",
	"name": "face_with_open_eyes_and_hand_over_mouth"
  },
  {
	"code": "1fae3",
	"name": "face_with_peeking_eye"
  },
  {
	"code": "1fae1",
	"name": "saluting_face"
  },
  {
	"code": "1fae5",
	"name": "dotted_line_face"
  },
  {
	"code": "1f636-200d-1f32b",
	"name": "face_in_clouds"
  },
  {
	"code": "1f62e-200d-1f4a8",
	"name": "face_exhaling"
  },
  {
	"code": "1f635-200d-1f4ab",
	"name": "face_with_spiral_eyes"
  },
  {
	"code": "1fae4",
	"name": "face_with_diagonal_mouth"
  },
  {
	"code": "2639",
	"name": "frowning_face"
  },
  {
	"code": "1f979",
	"name": "face_holding_back_tears"
  },
  {
	"code": "2764-fe0f-200d-1f525",
	"name": "heart_on_fire"
  },
  {
	"code": "2764-fe0f-200d-1fa79",
	"name": "mending_heart"
  },
  {
	"code": "1f441-fe0f-200d-1f5e8",
	"name": "eye_in_speech_bubble"
  },
  {
	"code": "1faf1",
	"name": "rightwards_hand"
  },
  {
	"code": "1faf2",
	"name": "leftwards_hand"
  },
  {
	"code": "1faf3",
	"name": "palm_down_hand"
  },
  {
	"code": "1faf4",
	"name": "palm_up_hand"
  },
  {
	"code": "1faf0",
	"name": "hand_with_index_finger_and_thumb_crossed"
  },
  {
	"code": "1faf5",
	"name": "index_pointing_at_the_viewer"
  },
  {
	"code": "1faf6",
	"name": "heart_hands"
  },
  {
	"code": "1fae6",
	"name": "biting_lip"
  },
  {
	"code": "1f9d4-200d-2642",
	"name": "man_beard"
  },
  {
	"code": "1f9d4-200d-2640",
	"name": "woman_beard"
  },
  {
	"code": "1f9d1-200d-1f9b0",
	"name": "person_red_hair"
  },
  {
	"code": "1f9d1-200d-1f9b1",
	"name": "person_curly_hair"
  },
  {
	"code": "1f9d1-200d-1f9b3",
	"name": "person_white_hair"
  },
  {
	"code": "1f9d1-200d-1f9b2",
	"name": "person_bald"
  },
  {
	"code": "1f471-200d-2642-fe0f",
	"name": "man_blond_hair"
  },
  {
	"code": "1f64d",
	"name": "person_frowning"
  },
  {
	"code": "1f64e",
	"name": "person_pouting"
  },
  {
	"code": "1f645",
	"name": "person_gesturing_no"
  },
  {
	"code": "1f646",
	"name": "person_gesturing_ok"
  },
  {
	"code": "1f481",
	"name": "person_tipping_hand"
  },
  {
	"code": "1f64b",
	"name": "person_raising_hand"
  },
  {
	"code": "1f9cf",
	"name": "deaf_person"
  },
  {
	"code": "1f647-200d-2642-fe0f",
	"name": "man_bowing"
  },
  {
	"code": "1f926",
	"name": "person_facepalming"
  },
  {
	"code": "1f937",
	"name": "person_shrugging"
  },
  {
	"code": "1f9d1-200d-2695-fe0f",
	"name": "health_worker"
  },
  {
	"code": "1f9d1-200d-1f393",
	"name": "student"
  },
  {
	"code": "1f9d1-200d-1f3eb",
	"name": "teacher"
  },
  {
	"code": "1f9d1-200d-2696-fe0f",
	"name": "judge"
  },
  {
	"code": "1f9d1-200d-1f33e",
	"name": "farmer"
  },
  {
	"code": "1f9d1-200d-1f373",
	"name": "cook"
  },
  {
	"code": "1f9d1-200d-1f527",
	"name": "mechanic"
  },
  {
	"code": "1f9d1-200d-1f3ed",
	"name": "factory_worker"
  },
  {
	"code": "1f9d1-200d-1f4bc",
	"name": "office_worker"
  },
  {
	"code": "1f9d1-200d-1f52c",
	"name": "scientist"
  },
  {
	"code": "1f9d1-200d-1f4bb",
	"name": "technologist"
  },
  {
	"code": "1f9d1-200d-1f3a4",
	"name": "singer"
  },
  {
	"code": "1f9d1-200d-1f3a8",
	"name": "artist"
  },
  {
	"code": "1f9d1-200d-2708-fe0f",
	"name": "pilot"
  },
  {
	"code": "1f9d1-200d-1f680",
	"name": "astronaut"
  },
  {
	"code": "1f9d1-200d-1f692",
	"name": "firefighter"
  },
  {
	"code": "1f46e-200d-2642-fe0f",
	"name": "man_police_officer"
  },
  {
	"code": "1f575-fe0f-200d-2642-fe0f",
	"name": "man_detective"
  },
  {
	"code": "1f482-200d-2642-fe0f",
	"name": "man_guard"
  },
  {
	"code": "1f477-200d-2642-fe0f",
	"name": "man_construction_worker"
  },
  {
	"code": "1fac5",
	"name": "person_with_crown"
  },
  {
	"code": "1f473-200d-2642-fe0f",
	"name": "man_wearing_turban"
  },
  {
	"code": "1f935-200d-2642-fe0f",
	"name": "man_in_tuxedo"
  },
  {
	"code": "1f935-200d-2640-fe0f",
	"name": "woman_in_tuxedo"
  },
  {
	"code": "1f470-200d-2642-fe0f",
	"name": "man_with_veil"
  },
  {
	"code": "1f470-200d-2640-fe0f",
	"name": "woman_with_veil"
  },
  {
	"code": "1fac3",
	"name": "pregnant_man"
  },
  {
	"code": "1fac4",
	"name": "pregnant_person"
  },
  {
	"code": "1f469-200d-1f37c",
	"name": "woman_feeding_baby"
  },
  {
	"code": "1f9d9-200d-2642-fe0f",
	"name": "man_mage"
  },
  {
	"code": "1f9da-200d-2642-fe0f",
	"name": "man_fairy"
  },
  {
	"code": "1f9da-200d-2640-fe0f",
	"name": "woman_fairy"
  },
  {
	"code": "1f9db-200d-2642-fe0f",
	"name": "man_vampire"
  },
  {
	"code": "1f9db-200d-2640-fe0f",
	"name": "woman_vampire"
  },
  {
	"code": "1f9dc-200d-2640-fe0f",
	"name": "mermaid"
  },
  {
	"code": "1f9dd-200d-2642-fe0f",
	"name": "man_elf"
  },
  {
	"code": "1f9dd-200d-2640-fe0f",
	"name": "woman_elf"
  },
  {
	"code": "1f9de-200d-2642",
	"name": "man_genie"
  },
  {
	"code": "1f9df-200d-2642",
	"name": "man_zombie"
  },
  {
	"code": "1f9cc",
	"name": "troll"
  },
  {
	"code": "1f486",
	"name": "person_getting_massage"
  },
  {
	"code": "1f487",
	"name": "person_getting_haircut"
  },
  {
	"code": "1f6b6-200d-2642-fe0f",
	"name": "man_walking"
  },
  {
	"code": "1f9cd",
	"name": "person_standing"
  },
  {
	"code": "1f9ce",
	"name": "person_kneeling"
  },
  {
	"code": "1f9d1-200d-1f9af",
	"name": "person_with_white_cane"
  },
  {
	"code": "1f9d1-200d-1f9bc",
	"name": "person_in_motorized_wheelchair"
  },
  {
	"code": "1f9d1-200d-1f9bd",
	"name": "person_in_manual_wheelchair"
  },
  {
	"code": "1f3c3-200d-2642-fe0f",
	"name": "man_running"
  },
  {
	"code": "1f46f-200d-2640",
	"name": "women_with_bunny_ears"
  },
  {
	"code": "1f9d6-200d-2642-fe0f",
	"name": "man_in_steamy_room"
  },
  {
	"code": "1f9d7-200d-2642-fe0f",
	"name": "man_climbing"
  },
  {
	"code": "1f3cc-fe0f-200d-2642-fe0f",
	"name": "man_golfing"
  },
  {
	"code": "1f3c4-200d-2642-fe0f",
	"name": "man_surfing"
  },
  {
	"code": "1f6a3-200d-2642-fe0f",
	"name": "man_rowing_boat"
  },
  {
	"code": "1f3ca-200d-2642-fe0f",
	"name": "man_swimming"
  },
  {
	"code": "26f9-fe0f-200d-2642-fe0f",
	"name": "man_bouncing_ball"
  },
  {
	"code": "1f3cb-fe0f-200d-2642-fe0f",
	"name": "man_lifting_weights"
  },
  {
	"code": "1f6b4-200d-2642-fe0f",
	"name": "man_biking"
  },
  {
	"code": "1f6b5-200d-2642-fe0f",
	"name": "man_mountain_biking"
  },
  {
	"code": "1f938",
	"name": "person_cartwheeling"
  },
  {
	"code": "1f93c",
	"name": "people_wrestling"
  },
  {
	"code": "1f93d",
	"name": "person_playing_water_polo"
  },
  {
	"code": "1f93e",
	"name": "person_playing_handball"
  },
  {
	"code": "1f939",
	"name": "person_juggling"
  },
  {
	"code": "1f9d8-200d-2642-fe0f",
	"name": "man_in_lotus_position"
  },
  {
	"code": "1f469-200d-2764-fe0f-200d-1f48b-200d-1f468",
	"name": "kiss_woman_man"
  },
  {
	"code": "1f469-200d-2764-fe0f-200d-1f468",
	"name": "couple_with_heart_woman_man"
  },
  {
	"code": "1f468-200d-1f469-200d-1f466",
	"name": "family_man_woman_boy"
  },
  {
	"code": "1f9b0",
	"name": "red_hair"
  },
  {
	"code": "1f9b1",
	"name": "curly_hair"
  },
  {
	"code": "1f9b3",
	"name": "white_hair"
  },
  {
	"code": "1f9b2",
	"name": "bald"
  },
  {
	"code": "1fab8",
	"name": "coral"
  },
  {
	"code": "1fab7",
	"name": "lotus"
  },
  {
	"code": "1fab9",
	"name": "empty_nest"
  },
  {
	"code": "1faba",
	"name": "nest_with_eggs"
  },
  {
	"code": "1fad8",
	"name": "beans"
  },
  {
	"code": "1fad7",
	"name": "pouring_liquid"
  },
  {
	"code": "1fad9",
	"name": "jar"
  },
  {
	"code": "1f6dd",
	"name": "playground_slide"
  },
  {
	"code": "1f6de",
	"name": "wheel"
  },
  {
	"code": "1f6df",
	"name": "ring_buoy"
  },
  {
	"code": "1faac",
	"name": "hamsa"
  },
  {
	"code": "1faa9",
	"name": "mirror_ball"
  },
  {
	"code": "1faab",
	"name": "low_battery"
  },
  {
	"code": "1fa7c",
	"name": "crutch"
  },
  {
	"code": "1fa7b",
	"name": "xray"
  },
  {
	"code": "1f6d7",
	"name": "elevator"
  },
  {
	"code": "1fae7",
	"name": "bubbles"
  },
  {
	"code": "1faaa",
	"name": "identification_card"
  },
  {
	"code": "23cf",
	"name": "eject_button"
  },
  {
	"code": "2640",
	"name": "female_sign"
  },
  {
	"code": "2642",
	"name": "male_sign"
  },
  {
	"code": "1f7f0",
	"name": "heavy_equals_sign"
  },
  {
	"code": "2695",
	"name": "medical_symbol"
  },
  {
	"code": "1f3f4-e0067-e0062-e0065-e006e-e0067-e007f",
	"name": "england"
  },
  {
	"code": "1f3f4-e0067-e0062-e0073-e0063-e0074-e007f",
	"name": "scotland"
  },
  {
	"code": "1f3f4-e0067-e0062-e0077-e006c-e0073-e007f",
	"name": "wales"
  }
]