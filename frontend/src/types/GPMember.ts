export interface GPMember {
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
  /**	User : Link - User	*/
  user?: string
}
