import {
  useEffect,
  useState,
} from "react";
import { useNavigate } from "react-router-dom";

import FloorPlanCanvas from "../components/FloorPlan/FloorPlanCanvas";
import generateFloorPlan from "../utils/generateFloorPlan";

function FloorPlan() {
  const navigate = useNavigate();

  const [project, setProject] =
    useState(null);

  const [layout, setLayout] =
    useState(null);

  const [floorPlan, setFloorPlan] =
    useState(null);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");

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

  useEffect(() => {
    if (!project || !layout?.building) {
      return;
    }

    let cancelled = false;

    async function createFloorPlan() {
      try {
        setLoading(true);
        setError("");

        const normalizedProject =
          normalizeProject(project);

        console.log(
          "========== FLOOR PLAN INPUT =========="
        );

        console.log(
          "Original project:",
          project
        );

        console.log(
          "Project sent to backend:",
          normalizedProject
        );

        console.log(
          "Project floors:",
          normalizedProject.floors
        );

        console.log(
          "Project bedrooms:",
          normalizedProject.bedrooms
        );

        console.log(
          "Project bathrooms:",
          normalizedProject.bathrooms
        );

        console.log(
          "Layout sent to backend:",
          layout
        );

        console.log(
          "Building:",
          layout?.building
        );

        console.log(
          "======================================"
        );

        const response =
          await generateFloorPlan(
            normalizedProject,
            layout
          );

        console.log(
          "Floor-plan response:",
          response
        );

        const generatedPlan =
          extractFloorPlan(response);

        if (!generatedPlan) {
          throw new Error(
            "The backend returned an empty floor plan."
          );
        }

        if (
          !Array.isArray(
            generatedPlan.rooms
          )
        ) {
          throw new Error(
            "The backend response does not contain a valid rooms array."
          );
        }

        const normalizedPlan =
          normalizeFloorPlan(
            generatedPlan,
            layout
          );

        if (
          normalizedPlan.width <= 0 ||
          normalizedPlan.height <= 0
        ) {
          throw new Error(
            "The generated plan has invalid dimensions."
          );
        }

        if (!cancelled) {
        setFloorPlan(normalizedPlan);
        }
        } catch (generationError) {
        console.error(
          "Unable to generate floor plan:",
          generationError
        );

        if (!cancelled) {
          setFloorPlan(null);

          setError(
            generationError?.message ||
              "Floor plan generation failed."
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    createFloorPlan();

    return () => {
      cancelled = true;
    };
  }, [project, layout]);

  if (loading) {
    return <LoadingScreen />;
  }

  if (!project || !layout?.building) {
    return (
      <main className="min-h-screen bg-slate-950 px-6 py-20 text-white">
        <div className="mx-auto max-w-xl text-center">
          <p className="text-sm font-semibold uppercase tracking-widest text-amber-400">
            Missing data
          </p>

          <h1 className="mt-3 text-3xl font-bold">
            Floor-plan data is missing
          </h1>

          <p className="mt-4 text-slate-400">
            Confirm the site layout before
            generating the floor plan.
          </p>

          <button
            type="button"
            onClick={() =>
              navigate("/site-planner")
            }
            className="mt-8 rounded-xl bg-emerald-500 px-6 py-3 font-semibold text-slate-950 transition hover:bg-emerald-400"
          >
            Open Site Planner
          </button>
        </div>
      </main>
    );
  }

  if (error || !floorPlan) {
    return (
      <main className="min-h-screen bg-slate-950 px-6 py-20 text-white">
        <div className="mx-auto max-w-xl text-center">
          <p className="text-sm font-semibold uppercase tracking-widest text-red-400">
            Generation error
          </p>

          <h1 className="mt-3 text-3xl font-bold">
            Floor plan generation failed
          </h1>

          <div className="mt-5 rounded-2xl border border-red-400/20 bg-red-400/10 p-4 text-sm text-red-200">
            {error ||
              "The backend did not return a valid floor plan."}
          </div>

          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <button
              type="button"
              onClick={() =>
                window.location.reload()
              }
              className="rounded-xl bg-emerald-500 px-6 py-3 font-semibold text-slate-950 transition hover:bg-emerald-400"
            >
              Try Again
            </button>

            <button
              type="button"
              onClick={() =>
                navigate("/site-planner")
              }
              className="rounded-xl border border-white/15 px-6 py-3 font-semibold transition hover:bg-white/5"
            >
              Back to Site Planner
            </button>
          </div>
        </div>
      </main>
    );
  }

  const unit =
    layout?.plot?.unit || "ft";

  const planWidth =
    safeNumber(floorPlan.width);

  const planHeight =
    safeNumber(floorPlan.height);

  const rooms =
    safeArray(floorPlan.rooms);

  const doors =
    safeArray(floorPlan.doors);

  const windows =
    safeArray(floorPlan.windows);

  const furniture =
    safeArray(floorPlan.furniture);

  const requestedFloors =
    positiveInteger(
      project?.floors,
      1
    );

  function handleSaveFloorPlan() {
  localStorage.setItem(
    "zynoraGeneratedFloorPlan",
    JSON.stringify(floorPlan)
  );

  navigate("/3d-design");
}

  return (
    <main className="min-h-screen bg-slate-950 px-5 py-10 text-white">
      <div className="mx-auto max-w-7xl">
        <header className="mb-8">
          <p className="text-sm font-semibold uppercase tracking-widest text-emerald-400">
            ZYNORA Floor Planner
          </p>

          <h1 className="mt-2 text-4xl font-bold">
            Architectural Floor Plan
          </h1>

          <p className="mt-3 max-w-2xl text-slate-400">
            Conceptual architectural plan
            generated from the confirmed
            building footprint.
          </p>
        </header>

        <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
          <div className="min-w-0 rounded-3xl border border-white/10 bg-white/5 p-4">
            <FloorPlanCanvas
              floorPlan={floorPlan}
              project={project}
            />
          </div>

          <aside className="rounded-3xl border border-white/10 bg-white/5 p-6">
            <h2 className="text-2xl font-semibold">
              Plan Information
            </h2>

            <div className="mt-6 space-y-4">
              <InfoRow
                label="Building length"
                value={`${planWidth.toFixed(
                  2
                )} ${unit}`}
              />

              <InfoRow
                label="Building width"
                value={`${planHeight.toFixed(
                  2
                )} ${unit}`}
              />

              <InfoRow
                label="Building area"
                value={`${(
                  planWidth *
                  planHeight
                ).toFixed(2)} sq ${unit}`}
              />

              <InfoRow
                label="Requested floors"
                value={requestedFloors}
              />

              <InfoRow
                label="Rooms"
                value={rooms.length}
              />

              <InfoRow
                label="Doors"
                value={doors.length}
              />

              <InfoRow
                label="Windows"
                value={windows.length}
              />

              <InfoRow
                label="Furniture"
                value={furniture.length}
              />

              <InfoRow
                label="Rotation"
                value={`${safeNumber(
                  floorPlan.rotation
                )}°`}
              />

              <InfoRow
                label="Match score"
                value={formatMatchScore(
                  floorPlan
                )}
              />

              <InfoRow
                label="Source plan"
                value={
                  floorPlan
                    ?.matched_plan
                    ?.name ||
                  floorPlan
                    ?.source_plan_id ||
                  "Not available"
                }
              />
            </div>

            {requestedFloors > 1 &&
              !Array.isArray(
                floorPlan.floors
              ) && (
                <div className="mt-6 rounded-xl border border-amber-400/20 bg-amber-400/10 p-4 text-sm text-amber-200">
                  The project requests{" "}
                  {requestedFloors} floors,
                  but the backend currently
                  returned one floor-plan
                  layout.
                </div>
              )}

            <button
  type="button"
  onClick={handleSaveFloorPlan}
  className="mt-8 w-full rounded-xl bg-emerald-500 px-5 py-3 font-semibold text-slate-950 transition hover:bg-emerald-400"
>
  Generate 3D Design
</button>

            <button
              type="button"
              onClick={() =>
                window.location.reload()
              }
              className="mt-3 w-full rounded-xl border border-emerald-400/30 px-5 py-3 font-semibold text-emerald-300 transition hover:bg-emerald-400/10"
            >
              Generate Again
            </button>

            <button
              type="button"
              onClick={() =>
                navigate("/site-planner")
              }
              className="mt-3 w-full rounded-xl border border-white/15 px-5 py-3 font-semibold transition hover:bg-white/5"
            >
              Back to Site Planner
            </button>
          </aside>
        </section>
      </div>
    </main>
  );
}

function normalizeProject(project) {
  const normalizedProject = {
    ...project,

    floors: String(
      positiveInteger(
        project?.floors ||
          project?.numberOfFloors,
        1
      )
    ),

    bedrooms: String(
      positiveInteger(
        project?.bedrooms ||
          project?.numberOfBedrooms,
        3
      )
    ),

    bathrooms: String(
      positiveInteger(
        project?.bathrooms ||
          project?.numberOfBathrooms,
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

function extractFloorPlan(response) {
  if (!response) {
    return null;
  }

  return (
    response.floor_plan ||
    response.adapted_plan ||
    response.generated_plan ||
    response.plan ||
    response
  );
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
    plan?.adapted_plan_dimensions ||
    plan?.dimensions ||
    {};

  return {
    ...plan,

    width:
      safeNumber(plan?.width) ||
      safeNumber(
        dimensions?.width
      ) ||
      fallbackLength,

    height:
      safeNumber(plan?.height) ||
      safeNumber(
        dimensions?.height
      ) ||
      fallbackWidth,

    rooms: safeArray(
      plan?.rooms
    ),

    doors: safeArray(
      plan?.doors
    ),

    windows: safeArray(
      plan?.windows
    ),

    furniture: safeArray(
      plan?.furniture
    ),

    floors: safeArray(
      plan?.floors
    ),

    rotation: safeNumber(
      plan?.rotation
    ),

    match_score:
      safeNumber(
        plan?.match_score
      ) ||
      safeNumber(
        plan?.matched_plan
          ?.match_score
      ),
  };
}

function positiveInteger(
  value,
  fallback
) {
  const numberValue =
    Number.parseInt(value, 10);

  if (
    Number.isInteger(numberValue) &&
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

function formatMatchScore(
  floorPlan
) {
  const score =
    safeNumber(
      floorPlan?.match_score
    ) ||
    safeNumber(
      floorPlan?.matched_plan
        ?.match_score
    );

  return score.toFixed(2);
}

function LoadingScreen() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 px-6 text-white">
      <div className="text-center">
        <div className="mx-auto h-12 w-12 animate-spin rounded-full border-4 border-slate-700 border-t-emerald-400" />

        <h1 className="mt-6 text-2xl font-bold">
          Generating your floor plan
        </h1>

        <p className="mt-3 text-slate-400">
          ZYNORA is selecting and adapting
          the best residential layout.
        </p>
      </div>
    </main>
  );
}

function InfoRow({
  label,
  value,
}) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-white/10 pb-3">
      <span className="text-sm text-slate-400">
        {label}
      </span>

      <strong className="max-w-[160px] break-words text-right text-sm">
        {value}
      </strong>
    </div>
  );
}

export default FloorPlan;