import { GPMember } from './GPMember'

export interface GPProject {
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
  /**	Title : Data	*/
  title: string
  /**	Progress : Percent	*/
  progress?: number
  /**	Icon : Data	*/
  icon?: string
  /**	Status : Select	*/
  status?: 'Open' | 'Completed'
  /**	Team : Link - GP Team	*/
  team?: string
  /**	Is Private : Check	*/
  is_private?: 0 | 1
  /**	Description : Text Editor	*/
  description?: string
  /**	Readme : Text Editor	*/
  readme?: string
  /**	Members : Table - GP Member	*/
  members: GPMember[]
  /**	Tasks Count : Int	*/
  tasks_count?: number
  /**	Discussions Count : Int	*/
  discussions_count?: number
  /**	Archived At : Datetime	*/
  archived_at?: string
  /**	Archived By : Link - User	*/
  archived_by?: string
  /**	Is Followed : Check	*/
  is_followed?: 0 | 1
}
