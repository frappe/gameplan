import { MaybeRefOrGetter, effectScope, toValue } from 'vue'

// Detached on purpose. An entry created while a component was setting up belongs to that
// component's scope, so its watchers and computeds stop the moment that component unmounts
// and every later caller inherits a dead object. This scope is never disposed, which is what
// a cache shared across mounts needs.
const documentScope = effectScope(true)

/**
 * Build a composable that shares one document instance per name.
 *
 * `create` is called once per name and receives that name as a plain string, so each entry
 * stays bound to the document it is filed under. Binding an entry to the caller's getter
 * instead is what made discussions and tasks open the wrong document: a route reuses one
 * page component across documents (opening a post from search while reading another one),
 * so the entry followed that component to the next document and then served it to whoever
 * asked for the original name next.
 *
 * The composable returns a view onto the entry for the caller's *current* name, resolved on
 * every property read. A caller whose name changes therefore keeps reading the right
 * document without re-running setup.
 */
export function createSharedDoc<T extends object>(create: (name: string) => T) {
  const cache: Record<string, T> = {}

  function entryFor(name: MaybeRefOrGetter<string>): T {
    const key = String(toValue(name) ?? '')
    if (!cache[key]) {
      cache[key] = documentScope.run(() => create(key)) as T
    }
    return cache[key]
  }

  return function useSharedDoc(name: MaybeRefOrGetter<string>): T {
    return new Proxy({} as T, {
      get: (_target, property) => Reflect.get(entryFor(name), property),
      has: (_target, property) => Reflect.has(entryFor(name), property),
      ownKeys: () => Reflect.ownKeys(entryFor(name)),
      getOwnPropertyDescriptor: (_target, property) => {
        const descriptor = Reflect.getOwnPropertyDescriptor(entryFor(name), property)
        // The proxy target is an empty object, so a non-configurable descriptor for a key it
        // does not own would break the Proxy invariants and throw.
        return descriptor && { ...descriptor, configurable: true }
      },
    })
  }
}
