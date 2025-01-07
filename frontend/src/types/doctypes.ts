interface DocType {
  name: string
  creation: string
  modified: string
  owner: string
  modified_by: string
}

interface ChildDocType extends DocType {
  parent?: string
  parentfield?: string
  parenttype?: string
  idx?: number
}

// Last updated: 2023-06-15 21:01:42.058336
export interface GPTask extends DocType {
  /** Title: Data */
  title: string
  /** Description: Text Editor */
  description?: string
  /** Start Date: Date */
  start_date?: string
  /** Due Date: Date */
  due_date?: string
  /** Status: Select */
  status: 'Backlog' | 'Todo' | 'In Progress' | 'Done' | 'Canceled'
  /** Priority: Select */
  priority?: '' | 'Urgent' | 'High' | 'Medium' | 'Low'
  /** Is Completed: Check */
  is_completed: 0 | 1
  /** Project: Link (GP Project) */
  project?: string
  /** Index: Int */
  idx?: number
  /** Team: Link (GP Team) */
  team?: string
  /** Assigned To: Link (User) */
  assigned_to?: string
  /** Completed At: Datetime */
  completed_at?: string
  /** Completed By: Data */
  completed_by?: string
  /** Comments Count: Int */
  comments_count?: number
}

// Last updated: 2023-01-16 13:19:48.202430
export interface GPUserProfile extends DocType {
  /** User: Link (User) */
  user: string
  /** Readme: Text Editor */
  readme?: string
  /** Full Name: Data */
  full_name?: string
  /** Cover Image: Attach Image */
  cover_image?: string
  /** Cover Image Position: Float */
  cover_image_position?: number
  /** Bio: Data */
  bio?: string
  /** Image: Attach Image */
  image?: string
  /** Is Image Background Removed: Check */
  is_image_background_removed: 0 | 1
  /** Original Image: Attach Image */
  original_image?: string
  /** Image Background Color: Color */
  image_background_color?: string
  /** Enabled: Check */
  enabled: 0 | 1
}

// Last updated: 2024-02-06 12:18:02.871772
export interface GPPage extends DocType {
  /** Title: Data */
  title?: string
  /** Content: Text Editor */
  content?: string
  /** Project: Link (GP Project) */
  project?: string
  /** Slug: Data */
  slug?: string
  /** User: Link (User) */
  user?: string
  /** Team: Link (GP Team) */
  team?: string
}

// Last updated: 2022-12-09 12:53:23.011368
export interface GPMember extends ChildDocType {
  /** User: Link (User) */
  user?: string
}

// Last updated: 2023-01-12 16:56:50.063064
export interface GPNotification extends DocType {
  /** From User: Link (User) */
  from_user?: string
  /** To User: Link (User) */
  to_user: string
  /** Type: Select */
  type: 'Mention' | 'Reaction'
  /** Message: Text Editor */
  message?: string
  /** Read: Check */
  read: 0 | 1
  /** Comment: Link (GP Comment) */
  comment?: string
  /** Discussion: Link (GP Discussion) */
  discussion?: string
  /** Task: Link (GP Task) */
  task?: string
  /** Project: Link (GP Project) */
  project?: string
  /** Team: Link (GP Team) */
  team?: string
}

// Last updated: 2024-02-06 12:11:11.919002
export interface GPDiscussion extends DocType {
  /** Project: Link (GP Project) */
  project: string
  /** Content: Text Editor */
  content?: string
  /** Status: Data */
  status?: string
  /** Title: Data */
  title: string
  /** Reactions: Table (GP Reaction) */
  reactions: GPReaction[]
  /** Team: Link (GP Team) */
  team?: string
  /** Last Post At: Datetime */
  last_post_at?: string
  /** Comments Count: Int */
  comments_count?: number
  /** Last Post By: Link (User) */
  last_post_by?: string
  /** Closed At: Datetime */
  closed_at?: string
  /** Closed By: Link (User) */
  closed_by?: string
  /** Slug: Data */
  slug?: string
  /** Participants Count: Int */
  participants_count: number
  /** Pinned At: Datetime */
  pinned_at?: string
  /** Pinned By: Link (User) */
  pinned_by?: string
}

// Last updated: 2023-02-13 21:00:23.191195
export interface GPTeam extends DocType {
  /** Title: Data */
  title: string
  /** Cover Image: Attach Image */
  cover_image?: string
  /** Members: Table (GP Member) */
  members: GPMember[]
  /** Cover Image Position: Float */
  cover_image_position?: number
  /** Icon: Data */
  icon?: string
  /** Readme: Text Editor */
  readme?: string
  /** Archived At: Datetime */
  archived_at?: string
  /** Archived By: Link (User) */
  archived_by?: string
  /** Is Private: Check */
  is_private: 0 | 1
}

// Last updated: 2023-05-08 16:57:35.133580
export interface GPGuestAccess extends DocType {
  /** User: Link (User) */
  user: string
  /** Project: Link (GP Project) */
  project: string
  /** Team: Link (GP Team) */
  team?: string
}

// Last updated: 2023-05-08 16:58:26.857607
export interface GPInvitation extends DocType {
  /** Email: Data */
  email: string
  /** Key: Data */
  key?: string
  /** Status: Select */
  status?: '' | 'Pending' | 'Accepted' | 'Expired'
  /** Email Sent At: Datetime */
  email_sent_at?: string
  /** Invited By: Link (User) */
  invited_by?: string
  /** Accepted At: Datetime */
  accepted_at?: string
  /** Teams: Small Text */
  teams?: string
  /** Projects: Small Text */
  projects?: string
  /** Role: Select */
  role: '' | 'Gameplan Admin' | 'Gameplan Member' | 'Gameplan Guest'
}

// Last updated: 2024-12-15 00:46:16.394764
export interface GPProject extends DocType {
  /** Title: Data */
  title: string
  /** Description: Text Editor */
  description?: string
  /** Team: Link (GP Team) */
  team?: string
  /** Members: Table (GP Member) */
  members: GPMember[]
  /** Icon: Data */
  icon?: string
  /** Readme: Text Editor */
  readme?: string
  /** Tasks Count: Int */
  tasks_count?: number
  /** Discussions Count: Int */
  discussions_count?: number
  /** Archived At: Datetime */
  archived_at?: string
  /** Archived By: Link (User) */
  archived_by?: string
  /** Is Private: Check */
  is_private: 0 | 1
  /** Is Followed: Check */
  is_followed: 0 | 1
}

// Last updated: 2022-08-11 18:36:55.799372
export interface GPReaction extends ChildDocType {
  /** Emoji: Data */
  emoji: string
  /** User: Data */
  user?: string
}

// Last updated: 2023-01-12 17:30:44.294192
export interface GPComment extends DocType {
  /** Content: Text Editor */
  content: string
  /** Reference DocType: Link (DocType) */
  reference_doctype?: string
  /** Reference Name: Dynamic Link (reference_doctype) */
  reference_name?: string
  /** Reactions: Table (GP Reaction) */
  reactions: GPReaction[]
  /** Deleted At: Datetime */
  deleted_at?: string
}

// Last updated: 2023-05-05 17:19:19.900086
export interface GPPollOption extends ChildDocType {
  /** Title: Data */
  title: string
  /** Percentage: Percent */
  percentage?: number
  /** Votes: Int */
  votes?: number
}

// Last updated: 2023-05-10 16:53:16.263855
export interface GPPollVote extends ChildDocType {
  /** User: Link (User) */
  user: string
  /** Option: Data */
  option?: string
}

// Last updated: 2023-09-08 00:06:11.732481
export interface GPPoll extends DocType {
  /** Title: Data */
  title: string
  /** Options: Table (GP Poll Option) */
  options: GPPollOption[]
  /** Multiple Answers: Check */
  multiple_answers: 0 | 1
  /** Anonymous: Check */
  anonymous: 0 | 1
  /** Discussion: Link (GP Discussion) */
  discussion?: string
  /** Votes: Table (GP Poll Vote) */
  votes: GPPollVote[]
  /** Total Votes: Int */
  total_votes?: number
  /** Stopped At: Datetime */
  stopped_at?: string
  /** Reactions: Table (GP Reaction) */
  reactions: GPReaction[]
}

// Last updated: 2022-12-07 21:34:41.411618
export interface GPActivity extends DocType {
  /** Reference DocType: Link (DocType) */
  reference_doctype?: string
  /** Reference Name: Dynamic Link (reference_doctype) */
  reference_name?: string
  /** User: Link (User) */
  user?: string
  /** Action: Data */
  action?: string
  /** Data: Code */
  data?: string
}
