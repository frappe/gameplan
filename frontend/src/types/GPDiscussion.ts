import { GPReaction } from './GPReaction'

export interface GPDiscussion {
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
  /**	Project : Link - GP Project	*/
  project: string
  /**	Team : Link - GP Team	*/
  team?: string
  /**	Status : Data	*/
  status?: string
  /**	Title : Data	*/
  title: string
  /**	Slug : Data	*/
  slug?: string
  /**	Content : Text Editor	*/
  content?: string
  /**	Reactions : Table - GP Reaction	*/
  reactions?: GPReaction[]
  /**	Last Post At : Datetime	*/
  last_post_at: string
  /**	Last Post By : Link - User	*/
  last_post_by?: string
  /**	Closed At : Datetime	*/
  closed_at?: string
  /**	Closed By : Link - User	*/
  closed_by?: string
  /**	Pinned At : Datetime	*/
  pinned_at?: string
  /**	Pinned By : Link - User	*/
  pinned_by?: string
  /**	Comments Count : Int	*/
  comments_count?: number
  /**	Participants Count : Int	*/
  participants_count?: number
}
