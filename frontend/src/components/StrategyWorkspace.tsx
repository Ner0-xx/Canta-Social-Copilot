import {
  AlertTriangle,
  Check,
  ChevronRight,
  Plus,
  Save,
  Trash2,
} from "lucide-react";
import { useMemo, useState } from "react";

import type {
  AudienceSegment,
  ContentPillar,
  Strategy,
} from "../types";
import { TagInput } from "./TagInput";

type WorkspaceTab = "identity" | "audience" | "pillars" | "voice" | "guardrails";

interface StrategyWorkspaceProps {
  strategy: Strategy;
  saving: boolean;
  onChange: (strategy: Strategy) => void;
  onSave: () => void;
}

const tabs: Array<{ id: WorkspaceTab; label: string }> = [
  { id: "identity", label: "Identity" },
  { id: "audience", label: "Audience" },
  { id: "pillars", label: "Content pillars" },
  { id: "voice", label: "Voice" },
  { id: "guardrails", label: "Guardrails" },
];

const blankAudience = (): AudienceSegment => ({
  name: "",
  description: "",
  needs: [],
  interests: [],
  desired_action: "",
});

const blankPillar = (): ContentPillar => ({
  name: "",
  description: "",
  target_percentage: 0,
  example_topics: [],
});

export function StrategyWorkspace({
  strategy,
  saving,
  onChange,
  onSave,
}: StrategyWorkspaceProps) {
  const [tab, setTab] = useState<WorkspaceTab>("identity");
  const pillarTotal = useMemo(
    () => strategy.pillars.reduce((sum, pillar) => sum + pillar.target_percentage, 0),
    [strategy.pillars],
  );

  const updateAudience = (index: number, next: AudienceSegment) => {
    const audiences = [...strategy.audiences];
    audiences[index] = next;
    onChange({ ...strategy, audiences });
  };

  const updatePillar = (index: number, next: ContentPillar) => {
    const pillars = [...strategy.pillars];
    pillars[index] = next;
    onChange({ ...strategy, pillars });
  };

  return (
    <div className="workspace">
      <div className="workspace-heading">
        <div>
          <p className="eyebrow">Strategy profile</p>
          <h1>Account direction</h1>
        </div>
        <button
          className="primary-button"
          type="button"
          onClick={onSave}
          disabled={saving || (strategy.pillars.length > 0 && pillarTotal !== 100)}
        >
          {saving ? <span className="spinner" /> : <Save size={17} />}
          {saving ? "Saving" : "Save strategy"}
        </button>
      </div>

      <div className="workspace-grid">
        <nav className="section-nav" aria-label="Strategy sections">
          {tabs.map((item) => (
            <button
              className={tab === item.id ? "section-nav-item active" : "section-nav-item"}
              key={item.id}
              type="button"
              onClick={() => setTab(item.id)}
            >
              <span>{item.label}</span>
              {tab === item.id && <ChevronRight size={16} />}
            </button>
          ))}
          <div className="profile-progress">
            <span>Profile readiness</span>
            <strong>{calculateReadiness(strategy)}%</strong>
            <div className="progress-track">
              <span style={{ width: `${calculateReadiness(strategy)}%` }} />
            </div>
          </div>
        </nav>

        <section className="form-surface">
          {tab === "identity" && (
            <div className="form-section">
              <SectionHeader
                title="Identity"
                description="The positioning used as context for every draft."
              />
              <div className="field-grid two-column">
                <div className="field">
                  <label htmlFor="display-name">Display name</label>
                  <input
                    id="display-name"
                    value={strategy.brand.display_name}
                    onChange={(event) =>
                      onChange({
                        ...strategy,
                        brand: { ...strategy.brand, display_name: event.target.value },
                      })
                    }
                  />
                </div>
                <div className="field">
                  <label htmlFor="account-purpose">Account purpose</label>
                  <input
                    id="account-purpose"
                    value={strategy.brand.account_purpose}
                    onChange={(event) =>
                      onChange({
                        ...strategy,
                        brand: { ...strategy.brand, account_purpose: event.target.value },
                      })
                    }
                  />
                </div>
              </div>
              <div className="field">
                <label htmlFor="biography">Working biography</label>
                <textarea
                  id="biography"
                  rows={5}
                  value={strategy.brand.biography}
                  onChange={(event) =>
                    onChange({
                      ...strategy,
                      brand: { ...strategy.brand, biography: event.target.value },
                    })
                  }
                />
              </div>
              <div className="field-grid two-column">
                <TagInput
                  id="expertise"
                  label="Areas of expertise"
                  values={strategy.brand.expertise}
                  placeholder="Add an area"
                  onChange={(expertise) =>
                    onChange({ ...strategy, brand: { ...strategy.brand, expertise } })
                  }
                />
                <TagInput
                  id="offers"
                  label="Offers"
                  values={strategy.brand.offers}
                  placeholder="Add an offer"
                  onChange={(offers) =>
                    onChange({ ...strategy, brand: { ...strategy.brand, offers } })
                  }
                />
              </div>
              <TagInput
                id="business-goals"
                label="Business goals"
                values={strategy.brand.business_goals}
                placeholder="Add a measurable goal"
                onChange={(business_goals) =>
                  onChange({
                    ...strategy,
                    brand: { ...strategy.brand, business_goals },
                  })
                }
              />
            </div>
          )}

          {tab === "audience" && (
            <div className="form-section">
              <SectionHeader
                title="Audience"
                description="The people each idea should help or move."
                action={
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() =>
                      onChange({
                        ...strategy,
                        audiences: [...strategy.audiences, blankAudience()],
                      })
                    }
                  >
                    <Plus size={16} />
                    Add segment
                  </button>
                }
              />
              {strategy.audiences.length === 0 ? (
                <EmptyState label="No audience segments yet." />
              ) : (
                <div className="repeat-list">
                  {strategy.audiences.map((audience, index) => (
                    <article className="repeat-item" key={audience.id ?? `new-${index}`}>
                      <div className="repeat-heading">
                        <span>Segment {index + 1}</span>
                        <button
                          className="icon-button danger"
                          type="button"
                          onClick={() =>
                            onChange({
                              ...strategy,
                              audiences: strategy.audiences.filter(
                                (_, itemIndex) => itemIndex !== index,
                              ),
                            })
                          }
                          aria-label={`Remove audience segment ${index + 1}`}
                          title="Remove segment"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                      <div className="field-grid two-column">
                        <div className="field">
                          <label htmlFor={`audience-name-${index}`}>Name</label>
                          <input
                            id={`audience-name-${index}`}
                            value={audience.name}
                            onChange={(event) =>
                              updateAudience(index, {
                                ...audience,
                                name: event.target.value,
                              })
                            }
                          />
                        </div>
                        <div className="field">
                          <label htmlFor={`audience-action-${index}`}>Desired action</label>
                          <input
                            id={`audience-action-${index}`}
                            value={audience.desired_action}
                            onChange={(event) =>
                              updateAudience(index, {
                                ...audience,
                                desired_action: event.target.value,
                              })
                            }
                          />
                        </div>
                      </div>
                      <div className="field">
                        <label htmlFor={`audience-description-${index}`}>Description</label>
                        <textarea
                          id={`audience-description-${index}`}
                          rows={3}
                          value={audience.description}
                          onChange={(event) =>
                            updateAudience(index, {
                              ...audience,
                              description: event.target.value,
                            })
                          }
                        />
                      </div>
                      <div className="field-grid two-column">
                        <TagInput
                          id={`audience-needs-${index}`}
                          label="Needs"
                          values={audience.needs}
                          placeholder="Add a need"
                          onChange={(needs) => updateAudience(index, { ...audience, needs })}
                        />
                        <TagInput
                          id={`audience-interests-${index}`}
                          label="Interests"
                          values={audience.interests}
                          placeholder="Add an interest"
                          onChange={(interests) =>
                            updateAudience(index, { ...audience, interests })
                          }
                        />
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </div>
          )}

          {tab === "pillars" && (
            <div className="form-section">
              <SectionHeader
                title="Content pillars"
                description="Target percentages must total 100%."
                action={
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() =>
                      onChange({
                        ...strategy,
                        pillars: [...strategy.pillars, blankPillar()],
                      })
                    }
                  >
                    <Plus size={16} />
                    Add pillar
                  </button>
                }
              />
              <div className={pillarTotal === 100 ? "total-strip valid" : "total-strip"}>
                {pillarTotal === 100 ? <Check size={16} /> : <AlertTriangle size={16} />}
                <span>Allocation</span>
                <strong>{pillarTotal}%</strong>
              </div>
              {strategy.pillars.length === 0 ? (
                <EmptyState label="No content pillars yet." />
              ) : (
                <div className="repeat-list">
                  {strategy.pillars.map((pillar, index) => (
                    <article className="repeat-item" key={pillar.id ?? `new-${index}`}>
                      <div className="repeat-heading">
                        <span>Pillar {index + 1}</span>
                        <button
                          className="icon-button danger"
                          type="button"
                          onClick={() =>
                            onChange({
                              ...strategy,
                              pillars: strategy.pillars.filter(
                                (_, itemIndex) => itemIndex !== index,
                              ),
                            })
                          }
                          aria-label={`Remove content pillar ${index + 1}`}
                          title="Remove pillar"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                      <div className="field-grid pillar-grid">
                        <div className="field">
                          <label htmlFor={`pillar-name-${index}`}>Name</label>
                          <input
                            id={`pillar-name-${index}`}
                            value={pillar.name}
                            onChange={(event) =>
                              updatePillar(index, { ...pillar, name: event.target.value })
                            }
                          />
                        </div>
                        <div className="field">
                          <label htmlFor={`pillar-percentage-${index}`}>Allocation</label>
                          <div className="number-input">
                            <input
                              id={`pillar-percentage-${index}`}
                              type="number"
                              min={0}
                              max={100}
                              value={pillar.target_percentage}
                              onChange={(event) =>
                                updatePillar(index, {
                                  ...pillar,
                                  target_percentage: Number(event.target.value),
                                })
                              }
                            />
                            <span>%</span>
                          </div>
                        </div>
                      </div>
                      <div className="field">
                        <label htmlFor={`pillar-description-${index}`}>Description</label>
                        <textarea
                          id={`pillar-description-${index}`}
                          rows={3}
                          value={pillar.description}
                          onChange={(event) =>
                            updatePillar(index, {
                              ...pillar,
                              description: event.target.value,
                            })
                          }
                        />
                      </div>
                      <TagInput
                        id={`pillar-topics-${index}`}
                        label="Example topics"
                        values={pillar.example_topics}
                        placeholder="Add a topic"
                        onChange={(example_topics) =>
                          updatePillar(index, { ...pillar, example_topics })
                        }
                      />
                    </article>
                  ))}
                </div>
              )}
            </div>
          )}

          {tab === "voice" && (
            <div className="form-section">
              <SectionHeader
                title="Voice"
                description="Language and writing patterns used during drafting."
              />
              <div className="field-grid two-column">
                <TagInput
                  id="tone"
                  label="Tone"
                  values={strategy.voice.tone}
                  placeholder="Add a quality"
                  onChange={(tone) =>
                    onChange({ ...strategy, voice: { ...strategy.voice, tone } })
                  }
                />
                <TagInput
                  id="preferred-vocabulary"
                  label="Preferred vocabulary"
                  values={strategy.voice.preferred_vocabulary}
                  placeholder="Add a word or phrase"
                  onChange={(preferred_vocabulary) =>
                    onChange({
                      ...strategy,
                      voice: { ...strategy.voice, preferred_vocabulary },
                    })
                  }
                />
              </div>
              <TagInput
                id="avoided-vocabulary"
                label="Avoided vocabulary"
                values={strategy.voice.avoided_vocabulary}
                placeholder="Add a word or phrase"
                onChange={(avoided_vocabulary) =>
                  onChange({
                    ...strategy,
                    voice: { ...strategy.voice, avoided_vocabulary },
                  })
                }
              />
              <div className="field-grid two-column">
                <div className="field">
                  <label htmlFor="formatting-preferences">Formatting preferences</label>
                  <textarea
                    id="formatting-preferences"
                    rows={5}
                    value={strategy.voice.formatting_preferences}
                    onChange={(event) =>
                      onChange({
                        ...strategy,
                        voice: {
                          ...strategy.voice,
                          formatting_preferences: event.target.value,
                        },
                      })
                    }
                  />
                </div>
                <div className="field">
                  <label htmlFor="cta-style">Call-to-action style</label>
                  <textarea
                    id="cta-style"
                    rows={5}
                    value={strategy.voice.call_to_action_style}
                    onChange={(event) =>
                      onChange({
                        ...strategy,
                        voice: {
                          ...strategy.voice,
                          call_to_action_style: event.target.value,
                        },
                      })
                    }
                  />
                </div>
              </div>
              <TagInput
                id="writing-examples"
                label="Short writing examples"
                values={strategy.voice.writing_examples}
                placeholder="Paste one representative example"
                onChange={(writing_examples) =>
                  onChange({
                    ...strategy,
                    voice: { ...strategy.voice, writing_examples },
                  })
                }
              />
            </div>
          )}

          {tab === "guardrails" && (
            <div className="form-section">
              <SectionHeader
                title="Guardrails"
                description="Content constraints applied before review."
              />
              <TagInput
                id="sensitive-topics"
                label="Sensitive or prohibited topics"
                values={strategy.brand.sensitive_topics}
                placeholder="Add a topic"
                onChange={(sensitive_topics) =>
                  onChange({
                    ...strategy,
                    brand: { ...strategy.brand, sensitive_topics },
                  })
                }
              />
              <TagInput
                id="required-disclosures"
                label="Required disclosures"
                values={strategy.brand.required_disclosures}
                placeholder="Add a disclosure"
                onChange={(required_disclosures) =>
                  onChange({
                    ...strategy,
                    brand: { ...strategy.brand, required_disclosures },
                  })
                }
              />
              <div className="policy-table">
                <PolicyRow label="Official API publishing" state="Approval required" />
                <PolicyRow label="Comments and replies" state="Individual approval" />
                <PolicyRow label="Restricted-data scraping" state="Blocked" blocked />
                <PolicyRow label="Browser automation" state="Blocked" blocked />
                <PolicyRow label="Security-control evasion" state="Blocked" blocked />
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function SectionHeader({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="section-heading">
      <div>
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
      {action}
    </div>
  );
}

function EmptyState({ label }: { label: string }) {
  return <div className="empty-state">{label}</div>;
}

function PolicyRow({
  label,
  state,
  blocked = false,
}: {
  label: string;
  state: string;
  blocked?: boolean;
}) {
  return (
    <div className="policy-row">
      <span>{label}</span>
      <strong className={blocked ? "blocked" : ""}>{state}</strong>
    </div>
  );
}

function calculateReadiness(strategy: Strategy): number {
  const checks = [
    strategy.brand.display_name.length > 0,
    strategy.brand.account_purpose.length > 0,
    strategy.brand.biography.length > 0,
    strategy.brand.expertise.length > 0,
    strategy.brand.business_goals.length > 0,
    strategy.audiences.length > 0,
    strategy.pillars.length > 0,
    strategy.voice.tone.length > 0,
    strategy.voice.writing_examples.length > 0,
    strategy.brand.sensitive_topics.length > 0,
  ];
  return Math.round((checks.filter(Boolean).length / checks.length) * 100);
}

