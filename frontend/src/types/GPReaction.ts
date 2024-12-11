export interface GPReaction {
  name: number
  creation: string
  modified: string
  owner: string
  modified_by: string
  docstatus: 0 | 1 | 2
  parent?: string
  parentfield?: string
  parenttype?: string
  idx?: number
  /**	Emoji : Data	*/
  emoji: string
  /**	User : Data	*/
  user?: string
}
