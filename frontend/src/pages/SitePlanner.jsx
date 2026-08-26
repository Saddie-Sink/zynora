import { useNavigate } from "react-router-dom";
import SitePlannerCanvas from "../components/SitePlanner/SitePlannerCanvas";

import "../assets/styles/siteplanner.css";


function SitePlanner() {
  const navigate = useNavigate();

  const storedResult =
    localStorage.getItem(
      "zynoraDesignResult"
    );

  const storedProject =
    localStorage.getItem(
      "zynoraProjectData"
    );

  let result = null;
  let project = null;

  try {
    result = storedResult
      ? JSON.parse(storedResult)
      : null;

    project = storedProject
      ? JSON.parse(storedProject)
      : null;
  } catch (error) {
    console.error(
      "Unable to read site planner data:",
      error
    );
  }

  if (!result || !project) {
    return (
      <main className="sp-page sp-state-page">
        <section className="sp-state-card">
          <p className="sp-eyebrow">
            ZYNORA SITE PLANNER
          </p>

          <h1>
            Site planning data is missing
          </h1>

          <p>
            Complete the project wizard
            and generate the design before
            opening the site planner.
          </p>

          <button
            type="button"
            className="sp-primary-button"
            onClick={() =>
              navigate("/create-project")
            }
          >
            Create Project
          </button>
        </section>
      </main>
    );
  }

  function handleConfirmLayout(
    layout
  ) {
    try {
      localStorage.setItem(
        "zynoraSiteLayout",
        JSON.stringify(layout)
      );

      navigate("/floor-plan");
    } catch (error) {
      console.error(
        "Unable to save site layout:",
        error
      );

      alert(
        "Unable to save the site layout. Please try again."
      );
    }
  }

  function handleBack() {
    navigate("/create-project");
  }

  return (
    <main className="sp-page">
      <div className="sp-shell">

        <header className="sp-header">
          <div>
            <p className="sp-eyebrow">
              ZYNORA SITE PLANNER
            </p>

            <h1>
              Position your building
            </h1>

            <p className="sp-header-copy">
              Enter the exact building
              dimensions, drag the building
              anywhere inside the plot, or
              enter an exact setback value.
              The building size remains fixed
              while its position changes.
            </p>
          </div>

          <button
            type="button"
            className="sp-secondary-button"
            onClick={handleBack}
          >
            Back to Project
          </button>
        </header>

        <section className="sp-step-grid">
          <StepCard
            number="1"
            title="Set size"
            description="Enter the building length and width."
          />

          <StepCard
            number="2"
            title="Position"
            description="Drag the building or edit any setback."
          />

          <StepCard
            number="3"
            title="Generate"
            description="Confirm the layout and create the 2D plan."
          />
        </section>

        <SitePlannerCanvas
          project={project}
          design={result.design}
          onConfirm={
            handleConfirmLayout
          }
        />

      </div>
    </main>
  );
}


function StepCard({
  number,
  title,
  description,
}) {
  return (
    <article className="sp-step-card">
      <div className="sp-step-number">
        {number}
      </div>

      <div>
        <h2>
          {title}
        </h2>

        <p>
          {description}
        </p>
      </div>
    </article>
  );
}


export default SitePlanner;
