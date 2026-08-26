import {
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

function clamp(value, minimum, maximum) {
  return Math.min(Math.max(value, minimum), maximum);
}

function round(value) {
  return Number(value.toFixed(2));
}

function SitePlannerCanvas({ project, design, onConfirm }) {
  const svgRef = useRef(null);

  const plotLength = Number(project.landLength) || 60;
  const plotWidth = Number(project.landWidth) || 40;
  const unit = project.measurementUnit || "ft";

  const initialBuildingLength = Math.min(
    Number(project.preferredBuildingLength) ||
      plotLength * 0.65,
    plotLength
  );

  const initialBuildingWidth = Math.min(
    Number(project.preferredBuildingWidth) ||
      plotWidth * 0.65,
    plotWidth
  );

  const getInitialBuilding = () => ({
    x: round(
      (plotLength - initialBuildingLength) / 2
    ),
    y: round(
      (plotWidth - initialBuildingWidth) / 2
    ),
    length: round(initialBuildingLength),
    width: round(initialBuildingWidth),
  });

  const [building, setBuilding] = useState(
    getInitialBuilding
  );

  const [dragOffset, setDragOffset] = useState(null);
  const [activeInput, setActiveInput] = useState(null);
  const [inputError, setInputError] = useState("");

  const [buildingInputs, setBuildingInputs] = useState({
    length: initialBuildingLength.toFixed(2),
    width: initialBuildingWidth.toFixed(2),
  });

  const [setbackInputs, setSetbackInputs] = useState({
    front: "",
    rear: "",
    left: "",
    right: "",
  });

  const measurements = useMemo(() => {
    const rear = building.y;
    const left = building.x;

    const front =
      plotWidth - building.y - building.width;

    const right =
      plotLength - building.x - building.length;

    const plotArea = plotLength * plotWidth;
    const buildingArea =
      building.length * building.width;

    const openArea = plotArea - buildingArea;

    const coverage =
      plotArea > 0
        ? (buildingArea / plotArea) * 100
        : 0;

    return {
      front: Math.max(0, front),
      rear: Math.max(0, rear),
      left: Math.max(0, left),
      right: Math.max(0, right),
      plotArea,
      buildingArea,
      openArea,
      coverage,
    };
  }, [building, plotLength, plotWidth]);

  useEffect(() => {
    setSetbackInputs((previous) => ({
      front:
        activeInput === "front"
          ? previous.front
          : measurements.front.toFixed(2),

      rear:
        activeInput === "rear"
          ? previous.rear
          : measurements.rear.toFixed(2),

      left:
        activeInput === "left"
          ? previous.left
          : measurements.left.toFixed(2),

      right:
        activeInput === "right"
          ? previous.right
          : measurements.right.toFixed(2),
    }));
  }, [measurements, activeInput]);

  function getPointerPosition(event) {
    const svg = svgRef.current;

    if (!svg) {
      return null;
    }

    const point = svg.createSVGPoint();

    point.x = event.clientX;
    point.y = event.clientY;

    const screenMatrix = svg.getScreenCTM();

    if (!screenMatrix) {
      return null;
    }

    return point.matrixTransform(
      screenMatrix.inverse()
    );
  }

  function handlePointerDown(event) {
    const pointer = getPointerPosition(event);

    if (!pointer) {
      return;
    }

    event.currentTarget.setPointerCapture(
      event.pointerId
    );

    setDragOffset({
      x: pointer.x - building.x,
      y: pointer.y - building.y,
    });

    setInputError("");
  }

  function handlePointerMove(event) {
    if (!dragOffset) {
      return;
    }

    const pointer = getPointerPosition(event);

    if (!pointer) {
      return;
    }

    const maximumX =
      plotLength - building.length;

    const maximumY =
      plotWidth - building.width;

    const nextX = clamp(
      pointer.x - dragOffset.x,
      0,
      maximumX
    );

    const nextY = clamp(
      pointer.y - dragOffset.y,
      0,
      maximumY
    );

    setBuilding((previous) => ({
      ...previous,
      x: round(nextX),
      y: round(nextY),
    }));
  }

  function stopDragging(event) {
    if (
      event.currentTarget.hasPointerCapture?.(
        event.pointerId
      )
    ) {
      event.currentTarget.releasePointerCapture(
        event.pointerId
      );
    }

    setDragOffset(null);
  }

  function handleBuildingInputChange(event) {
    const { name, value } = event.target;

    setBuildingInputs((previous) => ({
      ...previous,
      [name]: value,
    }));

    setInputError("");
  }

  function applyBuildingSize() {
    const requestedLength = Number(
      buildingInputs.length
    );

    const requestedWidth = Number(
      buildingInputs.width
    );

    if (
      !Number.isFinite(requestedLength) ||
      !Number.isFinite(requestedWidth) ||
      requestedLength <= 0 ||
      requestedWidth <= 0
    ) {
      setInputError(
        "Building length and width must be greater than zero."
      );

      return;
    }

    if (requestedLength > plotLength) {
      setInputError(
        `Building length cannot exceed ${plotLength} ${unit}.`
      );

      return;
    }

    if (requestedWidth > plotWidth) {
      setInputError(
        `Building width cannot exceed ${plotWidth} ${unit}.`
      );

      return;
    }

    setBuilding((previous) => {
      const nextX = clamp(
        previous.x,
        0,
        plotLength - requestedLength
      );

      const nextY = clamp(
        previous.y,
        0,
        plotWidth - requestedWidth
      );

      return {
        x: round(nextX),
        y: round(nextY),
        length: round(requestedLength),
        width: round(requestedWidth),
      };
    });

    setInputError("");
  }

  function handleSetbackInputChange(event) {
    const { name, value } = event.target;

    setSetbackInputs((previous) => ({
      ...previous,
      [name]: value,
    }));

    setInputError("");
  }

  function applySetback(name) {
    const requestedValue = Number(
      setbackInputs[name]
    );

    if (
      !Number.isFinite(requestedValue) ||
      requestedValue < 0
    ) {
      setInputError(
        `${capitalize(
          name
        )} setback must be zero or greater.`
      );

      return;
    }

    if (
      (name === "left" || name === "right") &&
      requestedValue >
        plotLength - building.length
    ) {
      setInputError(
        `${capitalize(
          name
        )} setback cannot exceed ${(
          plotLength - building.length
        ).toFixed(2)} ${unit}.`
      );

      return;
    }

    if (
      (name === "front" || name === "rear") &&
      requestedValue >
        plotWidth - building.width
    ) {
      setInputError(
        `${capitalize(
          name
        )} setback cannot exceed ${(
          plotWidth - building.width
        ).toFixed(2)} ${unit}.`
      );

      return;
    }

    setBuilding((previous) => {
      let nextX = previous.x;
      let nextY = previous.y;

      if (name === "left") {
        nextX = requestedValue;
      }

      if (name === "right") {
        nextX =
          plotLength -
          previous.length -
          requestedValue;
      }

      if (name === "rear") {
        nextY = requestedValue;
      }

      if (name === "front") {
        nextY =
          plotWidth -
          previous.width -
          requestedValue;
      }

      return {
        ...previous,
        x: round(nextX),
        y: round(nextY),
      };
    });

    setActiveInput(null);
    setInputError("");
  }

  function handleSetbackKeyDown(event) {
    if (event.key === "Enter") {
      event.preventDefault();
      applySetback(event.currentTarget.name);
      event.currentTarget.blur();
    }
  }

  function resetPlacement() {
    const initial = getInitialBuilding();

    setBuilding(initial);

    setBuildingInputs({
      length: initial.length.toFixed(2),
      width: initial.width.toFixed(2),
    });

    setInputError("");
    setActiveInput(null);
  }

  function centerBuilding() {
    setBuilding((previous) => ({
      ...previous,
      x: round(
        (plotLength - previous.length) / 2
      ),
      y: round(
        (plotWidth - previous.width) / 2
      ),
    }));

    setInputError("");
  }

  function confirmPlacement() {
    onConfirm({
      plot: {
        length: plotLength,
        width: plotWidth,
        unit,
      },

      building: {
        x: building.x,
        y: building.y,
        length: building.length,
        width: building.width,
      },

      setbacks: {
        front: measurements.front,
        rear: measurements.rear,
        left: measurements.left,
        right: measurements.right,
      },

      areas: {
        plotArea: measurements.plotArea,
        buildingArea: measurements.buildingArea,
        openArea: measurements.openArea,
        coverage: measurements.coverage,
      },
    });
  }

  return (
    <section className="sp-planner-grid">
      <div className="sp-plot-panel">
        <div className="sp-panel-heading">
          <div>
            <h2 className="sp-panel-title">
              Interactive Plot View
            </h2>

            <p className="sp-panel-copy">
              Set the building size and drag it anywhere
              inside the plot.
            </p>
          </div>

          <div className="sp-small-actions">
            <button
              type="button"
              onClick={centerBuilding}
              className="sp-small-button"
            >
              Center
            </button>

            <button
              type="button"
              onClick={resetPlacement}
              className="sp-small-button"
            >
              Reset
            </button>
          </div>
        </div>

        <div className="sp-plot-wrap">
          <svg
            ref={svgRef}
            viewBox={`-5 -5 ${plotLength + 10} ${
              plotWidth + 15
            }`}
            className="sp-site-svg"
            role="img"
            aria-label="Interactive site planner"
          >
            <rect
              x="0"
              y="0"
              width={plotLength}
              height={plotWidth}
              fill="white"
              stroke="#0f172a"
              strokeWidth="0.6"
            />

            <text
              x={plotLength / 2}
              y={-1.5}
              textAnchor="middle"
              fontSize="1.8"
              fill="#334155"
            >
              NORTH ↑
            </text>

            <SetbackGuides
              building={building}
              measurements={measurements}
              plotLength={plotLength}
              plotWidth={plotWidth}
              unit={unit}
            />

            <rect
              x={building.x}
              y={building.y}
              width={building.length}
              height={building.width}
              fill="#cbd5e1"
              stroke="#0f172a"
              strokeWidth="0.7"
              onPointerDown={handlePointerDown}
              onPointerMove={handlePointerMove}
              onPointerUp={stopDragging}
              onPointerCancel={stopDragging}
              style={{
                cursor: dragOffset
                  ? "grabbing"
                  : "grab",
              }}
            />

            <text
              x={
                building.x +
                building.length / 2
              }
              y={
                building.y +
                building.width / 2 -
                1
              }
              textAnchor="middle"
              dominantBaseline="middle"
              fontSize="2"
              fontWeight="700"
              fill="#0f172a"
              pointerEvents="none"
            >
              PROPOSED BUILDING
            </text>

            <text
              x={
                building.x +
                building.length / 2
              }
              y={
                building.y +
                building.width / 2 +
                2
              }
              textAnchor="middle"
              dominantBaseline="middle"
              fontSize="1.5"
              fill="#475569"
              pointerEvents="none"
            >
              {building.length.toFixed(1)} ×{" "}
              {building.width.toFixed(1)} {unit}
            </text>

            <line
              x1="0"
              y1={plotWidth + 3}
              x2={plotLength}
              y2={plotWidth + 3}
              stroke="#0f172a"
              strokeWidth="1.2"
            />

            <text
              x={plotLength / 2}
              y={plotWidth + 7}
              textAnchor="middle"
              fontSize="2"
              fontWeight="700"
              fill="#0f172a"
            >
              ROAD
            </text>
          </svg>
        </div>
      </div>

      <aside className="sp-controls-panel">
        <p className="sp-eyebrow">
          Site Controls
        </p>

        <h2 className="sp-controls-title">
          Building Placement
        </h2>

        <div className="sp-control-card">
          <h3 className="sp-control-card-title">
            Building dimensions
          </h3>

          <p className="sp-control-card-copy">
            These dimensions stay fixed while the
            building is moved.
          </p>

          <div className="sp-input-grid">
            <NumberInput
              label="Length"
              name="length"
              value={buildingInputs.length}
              unit={unit}
              onChange={handleBuildingInputChange}
            />

            <NumberInput
              label="Width"
              name="width"
              value={buildingInputs.width}
              unit={unit}
              onChange={handleBuildingInputChange}
            />
          </div>

          <button
            type="button"
            onClick={applyBuildingSize}
            className="sp-apply-button"
          >
            Apply Building Size
          </button>
        </div>

        <div className="sp-control-card">
          <h3 className="sp-control-card-title">
            Exact setbacks
          </h3>

          <p className="sp-control-card-copy">
            Edit any side. The building will move,
            while its size remains unchanged.
          </p>

          <div className="sp-input-grid">
            {["front", "rear", "left", "right"].map(
              (name) => (
                <SetbackInput
                  key={name}
                  label={capitalize(name)}
                  name={name}
                  value={setbackInputs[name]}
                  unit={unit}
                  onChange={
                    handleSetbackInputChange
                  }
                  onFocus={() =>
                    setActiveInput(name)
                  }
                  onBlur={() => applySetback(name)}
                  onKeyDown={
                    handleSetbackKeyDown
                  }
                />
              )
            )}
          </div>

          <p className="sp-help-text">
            Press Enter or click outside the field to
            apply a value.
          </p>
        </div>

        {inputError && (
          <p
            role="alert"
            className="sp-error-message"
          >
            {inputError}
          </p>
        )}

        <div className="sp-info-list">
          <InfoRow
            label="Plot size"
            value={`${plotLength.toFixed(
              1
            )} × ${plotWidth.toFixed(1)} ${unit}`}
          />

          <InfoRow
            label="Building size"
            value={`${building.length.toFixed(
              1
            )} × ${building.width.toFixed(
              1
            )} ${unit}`}
          />

          <InfoRow
            label="Building area"
            value={`${measurements.buildingArea.toFixed(
              2
            )} sq ${unit}`}
          />

          <InfoRow
            label="Open area"
            value={`${measurements.openArea.toFixed(
              2
            )} sq ${unit}`}
          />

          <InfoRow
            label="Coverage"
            value={`${measurements.coverage.toFixed(
              1
            )}%`}
          />
        </div>

        <button
          type="button"
          onClick={confirmPlacement}
          className="sp-confirm-button"
        >
          Confirm and Generate 2D Plan
        </button>

        <p className="sp-disclaimer">
          This output is conceptual. Construction
          dimensions and approval requirements must be
          checked by a qualified professional.
        </p>
      </aside>
    </section>
  );
}

function SetbackGuides({
  building,
  measurements,
  plotLength,
  plotWidth,
  unit,
}) {
  const centerX =
    building.x + building.length / 2;

  const centerY =
    building.y + building.width / 2;

  return (
    <g pointerEvents="none">
      <MeasurementLine
        x1={centerX}
        y1="0"
        x2={centerX}
        y2={building.y}
        label={`${measurements.rear.toFixed(
          1
        )} ${unit}`}
      />

      <MeasurementLine
        x1={centerX}
        y1={building.y + building.width}
        x2={centerX}
        y2={plotWidth}
        label={`${measurements.front.toFixed(
          1
        )} ${unit}`}
      />

      <MeasurementLine
        x1="0"
        y1={centerY}
        x2={building.x}
        y2={centerY}
        label={`${measurements.left.toFixed(
          1
        )} ${unit}`}
      />

      <MeasurementLine
        x1={building.x + building.length}
        y1={centerY}
        x2={plotLength}
        y2={centerY}
        label={`${measurements.right.toFixed(
          1
        )} ${unit}`}
      />
    </g>
  );
}

function MeasurementLine({
  x1,
  y1,
  x2,
  y2,
  label,
}) {
  const middleX =
    (Number(x1) + Number(x2)) / 2;

  const middleY =
    (Number(y1) + Number(y2)) / 2;

  const distance = Math.hypot(
    Number(x2) - Number(x1),
    Number(y2) - Number(y1)
  );

  if (distance < 0.8) {
    return null;
  }

  return (
    <g>
      <line
        x1={x1}
        y1={y1}
        x2={x2}
        y2={y2}
        stroke="#64748b"
        strokeWidth="0.25"
        strokeDasharray="0.8 0.6"
      />

      <text
        x={middleX}
        y={middleY - 0.5}
        textAnchor="middle"
        dominantBaseline="middle"
        fontSize="1.15"
        fontWeight="600"
        fill="#475569"
      >
        {label}
      </text>
    </g>
  );
}

function NumberInput({
  label,
  name,
  value,
  unit,
  onChange,
}) {
  return (
    <label className="sp-field">
      <span className="sp-field-label">
        {label}
      </span>

      <div className="sp-input-shell">
        <input
          type="number"
          name={name}
          value={value}
          onChange={onChange}
          min="0.1"
          step="0.25"
          className="sp-number-input"
        />

        <span className="sp-unit">
          {unit}
        </span>
      </div>
    </label>
  );
}

function SetbackInput({
  label,
  name,
  value,
  unit,
  onChange,
  onFocus,
  onBlur,
  onKeyDown,
}) {
  return (
    <label className="sp-field">
      <span className="sp-field-label">
        {label}
      </span>

      <div className="sp-input-shell">
        <input
          type="number"
          name={name}
          value={value}
          onChange={onChange}
          onFocus={onFocus}
          onBlur={onBlur}
          onKeyDown={onKeyDown}
          min="0"
          step="0.25"
          className="sp-number-input"
        />

        <span className="sp-unit">
          {unit}
        </span>
      </div>
    </label>
  );
}

function InfoRow({ label, value }) {
  return (
    <div className="sp-info-row">
      <span className="sp-info-label">
        {label}
      </span>

      <strong className="sp-info-value">
        {value}
      </strong>
    </div>
  );
}

function capitalize(value) {
  return (
    value.charAt(0).toUpperCase() +
    value.slice(1)
  );
}

export default SitePlannerCanvas;