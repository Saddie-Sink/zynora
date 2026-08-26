import {
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  useNavigate,
} from "react-router-dom";

import FloorPlanCanvas from "../components/FloorPlan/FloorPlanCanvas";
import generateFloorPlan from "../utils/generateFloorPlan";

import "../assets/styles/floorplan.css";


function FloorPlan() {
  const navigate = useNavigate();

  const [project, setProject] =
    useState(null);

  const [layout, setLayout] =
    useState(null);

  const [candidates, setCandidates] =
    useState([]);

  const [
    selectedCandidateId,
    setSelectedCandidateId,
  ] = useState(null);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");

  const [
    backendSummary,
    setBackendSummary,
  ] = useState({
    candidateCount: 0,
    rejectedCount: 0,
    recommendedId: null,
  });


  // ==========================================================
  // LOAD PROJECT + SITE LAYOUT
  // ==========================================================

  useEffect(() => {
    try {
      const storedProject =
        localStorage.getItem(
          "zynoraProjectData"
        );

      const storedLayout =
        localStorage.getItem(
          "zynoraSiteLayout"
        );

      const parsedProject =
        storedProject
          ? JSON.parse(storedProject)
          : null;

      const parsedLayout =
        storedLayout
          ? JSON.parse(storedLayout)
          : null;

      setProject(parsedProject);
      setLayout(parsedLayout);

      if (
        !parsedProject ||
        !parsedLayout?.building
      ) {
        setLoading(false);
      }
    } catch (storageError) {
      console.error(
        "Unable to read saved data:",
        storageError
      );

      setError(
        "The saved project or site-layout data could not be read."
      );

      setLoading(false);
    }
  }, []);


  // ==========================================================
  // GENERATE THREE CANDIDATES
  // ==========================================================

  useEffect(() => {
    if (
      !project ||
      !layout?.building
    ) {
      return;
    }

    let cancelled = false;

    async function createCandidates() {
      try {
        setLoading(true);
        setError("");

        const normalizedProject =
          normalizeProject(project);

        const response =
          await generateFloorPlan(
            normalizedProject,
            layout
          );

        console.log(
          "ZYNORA floor-plan response:",
          response
        );

        const rawCandidates =
          extractCandidates(response);

        if (
          !Array.isArray(rawCandidates) ||
          rawCandidates.length === 0
        ) {
          throw new Error(
            "The backend did not return any floor-plan candidates."
          );
        }

        const normalizedCandidates =
          rawCandidates
            .map((candidate, index) =>
              normalizeCandidate(
                candidate,
                layout,
                index
              )
            )
            .filter(
              (candidate) =>
                candidate?.plan &&
                Array.isArray(
                  candidate.plan.rooms
                )
            )
            .sort(
              (a, b) =>
                getCandidateRank(a) -
                getCandidateRank(b)
            );

        if (
          normalizedCandidates.length === 0
        ) {
          throw new Error(
            "The returned candidates did not contain valid floor-plan geometry."
          );
        }

        if (!cancelled) {
          setCandidates(
            normalizedCandidates
          );

          setBackendSummary({
            candidateCount:
              Number(
                response?.candidate_count
              ) ||
              normalizedCandidates.length,

            rejectedCount:
              Array.isArray(
                response?.rejected_candidates
              )
                ? response
                    .rejected_candidates
                    .length
                : 0,

            recommendedId:
              response
                ?.recommended_candidate_id ||
              null,
          });

          const recommended =
            normalizedCandidates.find(
              (candidate) =>
                candidate.recommended
            );

          setSelectedCandidateId(
            recommended?.id ||
              response
                ?.recommended_candidate_id ||
              normalizedCandidates[0]?.id
          );
        }
      } catch (generationError) {
        console.error(
          "Unable to generate candidates:",
          generationError
        );

        if (!cancelled) {
          setCandidates([]);

          setError(
            generationError?.message ||
              "Floor-plan generation failed."
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    createCandidates();

    return () => {
      cancelled = true;
    };
  }, [project, layout]);


  const selectedCandidate =
    useMemo(
      () =>
        candidates.find(
          (candidate) =>
            candidate.id ===
            selectedCandidateId
        ) ||
        candidates[0] ||
        null,
      [
        candidates,
        selectedCandidateId,
      ]
    );


  // ==========================================================
  // PAGE STATES
  // ==========================================================

  if (loading) {
    return <LoadingScreen />;
  }

  if (
    !project ||
    !layout?.building
  ) {
    return (
      <main className="fp-page">
        <section className="fp-state-card">
          <p className="fp-eyebrow">
            ZYNORA FLOOR PLANNER
          </p>

          <h1>
            Site planning data is missing
          </h1>

          <p>
            Confirm your site layout before
            generating floor-plan options.
          </p>

          <button
            type="button"
            className="fp-primary-button"
            onClick={() =>
              navigate("/site-planner")
            }
          >
            Open Site Planner
          </button>
        </section>
      </main>
    );
  }

  if (
    error ||
    candidates.length === 0
  ) {
    return (
      <main className="fp-page">
        <section className="fp-state-card fp-error-card">
          <p className="fp-eyebrow">
            GENERATION ERROR
          </p>

          <h1>
            Floor-plan generation failed
          </h1>

          <p>
            {error ||
              "No valid candidates were returned."}
          </p>

          <div className="fp-state-actions">
            <button
              type="button"
              className="fp-primary-button"
              onClick={() =>
                window.location.reload()
              }
            >
              Try Again
            </button>

            <button
              type="button"
              className="fp-secondary-button"
              onClick={() =>
                navigate("/site-planner")
              }
            >
              Back to Site Planner
            </button>
          </div>
        </section>
      </main>
    );
  }


  // ==========================================================
  // ACTIONS
  // ==========================================================

  function handleSelect(
    candidateId
  ) {
    setSelectedCandidateId(
      candidateId
    );
  }


  function handleContinue() {
    if (!selectedCandidate?.plan) {
      return;
    }

    localStorage.setItem(
      "zynoraSelectedFloorPlan",
      JSON.stringify(
        selectedCandidate
      )
    );

    localStorage.setItem(
      "zynoraGeneratedFloorPlan",
      JSON.stringify(
        selectedCandidate.plan
      )
    );

    navigate("/3d-design");
  }


  // ==========================================================
  // MAIN UI
  // ==========================================================

  return (
    <main className="fp-page">
      <div className="fp-shell">

        <header className="fp-header">
          <div>
            <p className="fp-eyebrow">
              ZYNORA AI FLOOR PLANNER
            </p>

            <h1>
              Choose Your Floor Plan
            </h1>

            <p className="fp-header-copy">
              ZYNORA generated three
              personalized layouts and ranked
              them using the trained
              machine-learning layout model.
            </p>
          </div>

          <div className="fp-backend-status">
            <span>
              {
                backendSummary
                  .candidateCount
              }{" "}
              valid options
            </span>

            <span>
              {
                backendSummary
                  .rejectedCount
              }{" "}
              rejected
            </span>
          </div>
        </header>


        <section className="fp-project-strip">
          <ProjectStat
            label="PROJECT"
            value={
              project?.name ||
              "Generated Home"
            }
          />

          <ProjectStat
            label="BUILDING"
            value={`${formatNumber(
              layout?.building?.length
            )}' × ${formatNumber(
              layout?.building?.width
            )}'`}
          />

          <ProjectStat
            label="BEDROOMS"
            value={
              project?.bedrooms ||
              "—"
            }
          />

          <ProjectStat
            label="BATHROOMS"
            value={
              project?.bathrooms ||
              "—"
            }
          />

          <ProjectStat
            label="FLOORS"
            value={
              project?.floors ||
              "—"
            }
          />
        </section>


        <section className="fp-candidate-grid">
          {candidates.map(
            (
              candidate,
              index
            ) => {
              const selected =
                candidate.id ===
                selectedCandidate?.id;

              const plan =
                candidate.plan;

              const floors =
                getFloorPlans(plan);

              return (
                <article
                  key={
                    candidate.id ||
                    index
                  }
                  className={[
                    "fp-candidate-card",
                    selected
                      ? "is-selected"
                      : "",
                    candidate.recommended
                      ? "is-recommended"
                      : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                >
                  <div className="fp-card-top">
                    <div>
                      <p className="fp-option-label">
                        OPTION{" "}
                        {String.fromCharCode(
                          65 + index
                        )}
                      </p>

                      <h2>
                        {candidate.title}
                      </h2>

                      <p className="fp-strategy">
                        {formatStrategy(
                          candidate.strategy
                        )}
                      </p>
                    </div>

                    <div className="fp-score-area">
                      {candidate.recommended && (
                        <span className="fp-recommended-badge">
                          ★ RECOMMENDED
                        </span>
                      )}

                      <strong>
                        {formatMLScore(
                          candidate
                        )}
                      </strong>

                      <span>
                        ML MATCH
                      </span>
                    </div>
                  </div>


                  <div className="fp-reason-box">
                    <p>
                      Why ZYNORA recommends
                      this option
                    </p>

                    <ul>
                      {getReasons(
                        candidate
                      ).map(
                        (
                          reason,
                          reasonIndex
                        ) => (
                          <li
                            key={
                              reasonIndex
                            }
                          >
                            ✓ {reason}
                          </li>
                        )
                      )}
                    </ul>
                  </div>


                  <div className="fp-floor-stack">
                    {floors.map(
                      (
                        floor,
                        floorIndex
                      ) => {
                        const floorName =
                          floor.name ||
                          getFloorName(
                            floorIndex
                          );

                        return (
                          <section
                            className="fp-floor-card"
                            key={
                              floor.level ??
                              floorIndex
                            }
                          >
                            <div className="fp-floor-heading">
                              <div>
                                <h3>
                                  {floorName}
                                </h3>

                                <p>
                                  {
                                    safeArray(
                                      floor.rooms
                                    ).length
                                  }{" "}
                                  spaces
                                </p>
                              </div>

                              <span>
                                {
                                  plan.width
                                }'
                                {" × "}
                                {
                                  plan.height
                                }'
                              </span>
                            </div>

                            <div className="fp-canvas-frame">
                              <FloorPlanCanvas
                                floorPlan={
                                  createFloorPreview(
                                    plan,
                                    floor,
                                    floorIndex
                                  )
                                }
                                project={
                                  project
                                }
                                preview
                                floorName={
                                  floorName
                                }
                              />
                            </div>
                          </section>
                        );
                      }
                    )}
                  </div>


                  <div className="fp-plan-stats">
                    <MiniStat
                      label="ROOMS"
                      value={
                        safeArray(
                          plan.rooms
                        ).length
                      }
                    />

                    <MiniStat
                      label="DOORS"
                      value={
                        safeArray(
                          plan.doors
                        ).length
                      }
                    />

                    <MiniStat
                      label="WINDOWS"
                      value={
                        safeArray(
                          plan.windows
                        ).length
                      }
                    />
                  </div>


                  <div className="fp-bath-summary">
                    <span>
                      Indoor bathrooms:
                      {" "}
                      <strong>
                        {
                          plan
                            .indoor_bathrooms ??
                          plan
                            .actual_bathrooms ??
                          "—"
                        }
                      </strong>
                    </span>

                    <span>
                      External:
                      {" "}
                      <strong>
                        {
                          plan
                            .external_bathrooms ??
                          0
                        }
                      </strong>
                    </span>
                  </div>


                  <button
                    type="button"
                    className={
                      selected
                        ? "fp-select-button selected"
                        : "fp-select-button"
                    }
                    onClick={() =>
                      handleSelect(
                        candidate.id
                      )
                    }
                  >
                    {selected
                      ? "✓ Selected"
                      : "Select This Plan"}
                  </button>
                </article>
              );
            }
          )}
        </section>


        <section className="fp-current-selection">
          <div>
            <p className="fp-eyebrow">
              CURRENT SELECTION
            </p>

            <h2>
              {
                selectedCandidate
                  ?.title
              }
            </h2>

            <p>
              ML suitability:
              {" "}
              <strong>
                {formatMLScore(
                  selectedCandidate
                )}
              </strong>
            </p>
          </div>

          <div className="fp-selection-actions">
            <button
              type="button"
              className="fp-secondary-button"
              onClick={() =>
                navigate(
                  "/site-planner"
                )
              }
            >
              Back to Site Planner
            </button>

            <button
              type="button"
              className="fp-secondary-button"
              onClick={() =>
                window.location.reload()
              }
            >
              Generate New Options
            </button>

            <button
              type="button"
              className="fp-primary-button"
              onClick={
                handleContinue
              }
            >
              Create 3D From Selected Plan →
            </button>
          </div>
        </section>

      </div>
    </main>
  );
}


// ============================================================
// BACKEND RESPONSE HELPERS
// ============================================================

function extractCandidates(
  response
) {
  if (!response) {
    return [];
  }

  if (
    Array.isArray(
      response.candidates
    )
  ) {
    return response.candidates;
  }

  const oldPlan =
    response.floor_plan ||
    response.adapted_plan ||
    response.generated_plan ||
    response.plan;

  if (oldPlan) {
    return [
      {
        id: "candidate-a",
        title:
          "Generated Floor Plan",
        recommended: true,
        plan: oldPlan,
      },
    ];
  }

  if (
    Array.isArray(
      response.rooms
    )
  ) {
    return [
      {
        id: "candidate-a",
        title:
          "Generated Floor Plan",
        recommended: true,
        plan: response,
      },
    ];
  }

  return [];
}


function normalizeCandidate(
  candidate,
  layout,
  index
) {
  const rawPlan =
    candidate?.floor_plan ||
    candidate?.plan ||
    candidate?.generated_plan ||
    candidate?.adapted_plan ||
    candidate;

  const plan =
    normalizeFloorPlan(
      rawPlan,
      layout
    );

  return {
    ...candidate,

    id:
      candidate?.id ||
      `candidate-${index + 1}`,

    title:
      candidate?.title ||
      candidate?.name ||
      `Floor Plan ${index + 1}`,

    recommended:
      Boolean(
        candidate?.recommended
      ),

    plan,
  };
}


function getCandidateRank(
  candidate
) {
  const rank = Number(
    candidate?.ml_ranking?.rank
  );

  return Number.isFinite(rank)
    ? rank
    : 999;
}


function formatMLScore(
  candidate
) {
  const score = Number(
    candidate?.ml_ranking
      ?.ml_score
  );

  if (
    !Number.isFinite(score)
  ) {
    return "--";
  }

  return `${score.toFixed(1)}%`;
}


function getReasons(
  candidate
) {
  const reasons =
    safeArray(
      candidate?.ml_ranking
        ?.reasons
    );

  if (reasons.length > 0) {
    return reasons.slice(
      0,
      3
    );
  }

  if (
    candidate?.strategy ===
    "open_living"
  ) {
    return [
      "Larger connected living and family spaces.",
      "Efficient movement between shared spaces.",
      "Strong natural-light potential.",
    ];
  }

  if (
    candidate?.strategy ===
    "privacy"
  ) {
    return [
      "Stronger separation between private spaces.",
      "Quieter bedroom and family zones.",
      "Efficient circulation between floors.",
    ];
  }

  return [
    "Balanced distribution of social and private spaces.",
    "Strong accessibility support.",
    "Good overall layout efficiency.",
  ];
}


function formatStrategy(
  strategy
) {
  if (
    strategy ===
    "open_living"
  ) {
    return "Open social living";
  }

  if (
    strategy ===
    "privacy"
  ) {
    return "Privacy-first zoning";
  }

  return "Balanced family planning";
}


// ============================================================
// FLOOR HELPERS
// ============================================================

function getFloorPlans(plan) {
  if (
    Array.isArray(
      plan?.floor_plans
    ) &&
    plan.floor_plans.length > 0
  ) {
    return plan.floor_plans;
  }

  if (
    Array.isArray(
      plan?.floors
    ) &&
    plan.floors.length > 0
  ) {
    return plan.floors;
  }

  return [
    {
      level: 0,
      name: "Ground Floor",
      rooms:
        safeArray(
          plan?.rooms
        ),
      doors:
        safeArray(
          plan?.doors
        ),
      windows:
        safeArray(
          plan?.windows
        ),
      stairs:
        safeArray(
          plan?.stairs
        ),
    },
  ];
}


function createFloorPreview(
  fullPlan,
  floor,
  floorIndex
) {
  const level =
    floor?.level ??
    floorIndex;

  const floorRooms =
    safeArray(
      floor?.rooms
    );

  const roomIds =
    new Set(
      floorRooms.map(
        (room) =>
          room.id
      )
    );

  const floorFurniture =
    safeArray(
      fullPlan?.furniture
    ).filter(
      (item) =>
        roomIds.has(
          item?.room_id
        )
    );

  const floorDoors =
    safeArray(
      floor?.doors
    ).length > 0
      ? safeArray(
          floor?.doors
        )
      : safeArray(
          fullPlan?.doors
        ).filter(
          (door) =>
            Number(
              door?.floor_level
            ) ===
              Number(level) ||
            roomIds.has(
              door?.room_id
            ) ||
            roomIds.has(
              door
                ?.from_room_id
            ) ||
            roomIds.has(
              door
                ?.to_room_id
            )
        );

  const floorWindows =
    safeArray(
      floor?.windows
    ).length > 0
      ? safeArray(
          floor?.windows
        )
      : safeArray(
          fullPlan?.windows
        ).filter(
          (windowItem) =>
            Number(
              windowItem
                ?.floor_level
            ) ===
              Number(level) ||
            roomIds.has(
              windowItem
                ?.room_id
            )
        );

  return {
    ...fullPlan,

    id:
      `${fullPlan?.id ||
      "plan"}-floor-${level}`,

    rooms:
      floorRooms,

    doors:
      floorDoors,

    windows:
      floorWindows,

    furniture:
      floorFurniture,

    floor_plans: [
      floor,
    ],

    floors: [
      floor,
    ],

    active_floor_level:
      level,
  };
}


function getFloorName(
  index
) {
  if (index === 0) {
    return "Ground Floor";
  }

  if (index === 1) {
    return "First Floor";
  }

  if (index === 2) {
    return "Second Floor";
  }

  return `Floor ${index + 1}`;
}


// ============================================================
// PROJECT NORMALIZATION
// ============================================================

function normalizeProject(
  project
) {
  const normalizedProject = {
    ...project,

    floors: String(
      positiveInteger(
        project?.floors ||
          project
            ?.numberOfFloors,
        1
      )
    ),

    bedrooms: String(
      positiveInteger(
        project?.bedrooms ||
          project
            ?.numberOfBedrooms,
        3
      )
    ),

    bathrooms: String(
      positiveInteger(
        project?.bathrooms ||
          project
            ?.numberOfBathrooms,
        1
      )
    ),
  };

  localStorage.setItem(
    "zynoraProjectData",
    JSON.stringify(
      normalizedProject
    )
  );

  return normalizedProject;
}


function normalizeFloorPlan(
  plan,
  layout
) {
  const fallbackLength =
    safeNumber(
      layout?.building?.length
    );

  const fallbackWidth =
    safeNumber(
      layout?.building?.width
    );

  const dimensions =
    plan
      ?.adapted_plan_dimensions ||
    plan?.dimensions ||
    {};

  return {
    ...plan,

    width:
      safeNumber(
        plan?.width
      ) ||
      safeNumber(
        dimensions?.width
      ) ||
      fallbackLength,

    height:
      safeNumber(
        plan?.height
      ) ||
      safeNumber(
        dimensions?.height
      ) ||
      fallbackWidth,

    rooms:
      safeArray(
        plan?.rooms
      ),

    doors:
      safeArray(
        plan?.doors
      ),

    windows:
      safeArray(
        plan?.windows
      ),

    furniture:
      safeArray(
        plan?.furniture
      ),

    floor_plans:
      safeArray(
        plan?.floor_plans
      ),

    floors:
      safeArray(
        plan?.floors
      ),

    rotation:
      safeNumber(
        plan?.rotation
      ),
  };
}


// ============================================================
// SMALL UI COMPONENTS
// ============================================================

function ProjectStat({
  label,
  value,
}) {
  return (
    <div className="fp-project-stat">
      <span>
        {label}
      </span>

      <strong>
        {value}
      </strong>
    </div>
  );
}


function MiniStat({
  label,
  value,
}) {
  return (
    <div className="fp-mini-stat">
      <strong>
        {value}
      </strong>

      <span>
        {label}
      </span>
    </div>
  );
}


function LoadingScreen() {
  return (
    <main className="fp-page fp-loading-page">
      <section className="fp-state-card">
        <div className="fp-spinner" />

        <h1>
          Generating 3 floor-plan
          options
        </h1>

        <p>
          ZYNORA is generating layouts,
          validating the geometry and
          ranking the designs with the
          trained ML model.
        </p>
      </section>
    </main>
  );
}


// ============================================================
// GENERIC HELPERS
// ============================================================

function positiveInteger(
  value,
  fallback
) {
  const numberValue =
    Number.parseInt(
      value,
      10
    );

  if (
    Number.isInteger(
      numberValue
    ) &&
    numberValue > 0
  ) {
    return numberValue;
  }

  return fallback;
}


function safeArray(value) {
  return Array.isArray(value)
    ? value
    : [];
}


function safeNumber(value) {
  const numberValue =
    Number(value);

  return Number.isFinite(
    numberValue
  )
    ? numberValue
    : 0;
}


function formatNumber(value) {
  const numberValue =
    Number(value);

  if (
    !Number.isFinite(
      numberValue
    )
  ) {
    return "—";
  }

  return Number.isInteger(
    numberValue
  )
    ? String(numberValue)
    : numberValue.toFixed(1);
}


export default FloorPlan;
