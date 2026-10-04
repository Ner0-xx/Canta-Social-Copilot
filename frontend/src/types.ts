export interface BrandProfile {
  display_name: string;
  account_purpose: string;
  biography: string;
  expertise: string[];
  offers: string[];
  business_goals: string[];
  sensitive_topics: string[];
  required_disclosures: string[];
}

export interface VoiceProfile {
  tone: string[];
  preferred_vocabulary: string[];
  avoided_vocabulary: string[];
  formatting_preferences: string;
  call_to_action_style: string;
  writing_examples: string[];
}

export interface AudienceSegment {
  id?: number;
  name: string;
  description: string;
  needs: string[];
  interests: string[];
  desired_action: string;
}

export interface ContentPillar {
  id?: number;
  name: string;
  description: string;
  target_percentage: number;
  example_topics: string[];
}

export interface Strategy {
  brand: BrandProfile;
  voice: VoiceProfile;
  audiences: AudienceSegment[];
  pillars: ContentPillar[];
}

export type ReleaseLevel =
  | "observe"
  | "draft"
  | "approve"
  | "integrate"
  | "schedule";

export interface AppSettings {
  release_level: ReleaseLevel;
  publishing_enabled: boolean;
}

export interface SourceData {
  id: number;
  name: string;
  source_type: "rss" | "url" | "note";
  uri_or_content: string;
  status: string;
  last_fetched_at?: string;
  created_at: string;
  updated_at: string;
}

export interface SourceItemData {
  id: number;
  source_id?: number;
  title: string;
  author: string;
  url: string;
  content: string;
  canonical_url: string;
  content_hash: string;
  published_at?: string;
  ingested_at: string;
}

export interface ContentIdeaData {
  id: number;
  title: string;
  summary: string;
  status: string;
  source_type: string;
  source_ref: string;
  pillar_id?: number;
  audience_id?: number;
  relevance_score: number;
  proposed_angle: string;
  created_at: string;
  updated_at: string;
}

export interface ContentDraftData {
  id: number;
  idea_id: number;
  platform: string;
  variant_type: string;
  title: string;
  body: string;
  image_path?: string;
  experiment_id?: number;
  experiment_variant?: string;
  status: string;
  quality_score: number;
  warnings: string[];
  citations: Array<{ claim: string; source_url: string }>;
  version: number;
  created_at: string;
  updated_at: string;
}

export const emptyStrategy: Strategy = {
  brand: {
    display_name: "",
    account_purpose: "",
    biography: "",
    expertise: [],
    offers: [],
    business_goals: [],
    sensitive_topics: [],
    required_disclosures: [],
  },
  voice: {
    tone: [],
    preferred_vocabulary: [],
    avoided_vocabulary: [],
    formatting_preferences: "",
    call_to_action_style: "",
    writing_examples: [],
  },
  audiences: [],
  pillars: [],
};

export interface ScheduledJob {
  id: number;
  draft_id: number;
  platform: string;
  scheduled_at: string;
  status: string;
  execution_log: Record<string, unknown>;
  created_at: string;
}

export interface AnalyticsTopPost {
  platform_post_id: string;
  platform: string;
  title: string;
  impressions: number;
  reactions: number;
}

export interface AnalyticsDashboardData {
  total_impressions: number;
  total_reactions: number;
  top_posts: AnalyticsTopPost[];
  pillar_performance: Array<{
    name: string;
    impressions: number;
    reactions: number;
  }>;
}

export interface RecentPublicationMetrics {
  impressions: number;
  reactions: number;
  comments: number;
  reposts: number;
}

export interface RecentPublicationData {
  platform_post_id: string;
  platform: string;
  title: string;
  published_at: string;
  metrics: RecentPublicationMetrics;
}

export interface EngagementInboxItem {
  id: string;
  platform: string;
  author: string;
  content: string;
  post_title: string;
}

export interface DraftReplyData {
  draft_reply: string;
}

export interface OAuthConnectionData {
  connected: boolean;
  platform: string;
  account_name?: string;
  expires_at?: string;
}

export interface AABExperimentData {
  id: number;
  name: string;
  hypothesis: string;
  start_date: string;
  end_date?: string;
  status: string;
  created_at: string;
  metrics?: Record<string, { impressions: number; reactions: number; posts: number }>;
}

export interface WeeklyReportData {
  id: number;
  week_start: string;
  week_end: string;
  total_impressions: number;
  total_reactions: number;
  top_pillar_id?: number;
  top_post_id?: string;
  insights_text: string;
  created_at: string;
}
