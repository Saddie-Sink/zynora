function FloorPlanCanvas({
  floorPlan,
  project,
  preview = false,
  floorName = "Floor Plan",
}) {
  if (!floorPlan) {
    return null;
  }

  const rooms = Array.isArray(
    floorPlan.rooms
  )
    ? floorPlan.rooms
    : [];

  const doors = Array.isArray(
    floorPlan.doors
  )
    ? floorPlan.doors
    : [];

  const windows = Array.isArray(
    floorPlan.windows
  )
    ? floorPlan.windows
    : [];

  const furniture = Array.isArray(
    floorPlan.furniture
  )
    ? floorPlan.furniture
    : [];

  const floorPlanWidth = Number(
    floorPlan.width || 0
  );

  const floorPlanHeight = Number(
    floorPlan.height || 0
  );

  if (
    floorPlanWidth <= 0 ||
    floorPlanHeight <= 0
  ) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
        The generated floor plan has invalid
        dimensions.
      </div>
    );
  }

  const sheetWidth = preview
    ? 900
    : 1200;

  const sheetHeight = preview
    ? 700
    : 780;

  const drawingAreaX = preview
    ? 55
    : 140;

  const drawingAreaY = preview
    ? 75
    : 120;

  const drawingAreaWidth = preview
    ? 790
    : 760;

  const drawingAreaHeight = preview
    ? 570
    : 550;

  const scale = Math.min(
    drawingAreaWidth / floorPlanWidth,
    drawingAreaHeight / floorPlanHeight
  );

  const renderedPlanWidth =
    floorPlanWidth * scale;

  const renderedPlanHeight =
    floorPlanHeight * scale;

  const planX =
    drawingAreaX +
    (
      drawingAreaWidth -
      renderedPlanWidth
    ) /
      2;

  const planY =
    drawingAreaY +
    (
      drawingAreaHeight -
      renderedPlanHeight
    ) /
      2;

  const projectName = String(
    project?.projectName ||
      project?.name ||
      "ZYNORA RESIDENCE"
  ).toUpperCase();

  return (
    <div
      className={
        preview
          ? "w-full overflow-hidden bg-white"
          : "overflow-auto rounded-2xl bg-slate-200 p-3"
      }
    >
      <svg
        viewBox={`0 0 ${sheetWidth} ${sheetHeight}`}
        preserveAspectRatio="xMidYMid meet"
        className="block h-auto w-full"
        role="img"
        aria-label={`ZYNORA ${floorName}`}
      >
        <defs>
          <pattern
            id="floor-grid"
            width="22"
            height="22"
            patternUnits="userSpaceOnUse"
          >
            <rect
              width="22"
              height="22"
              fill="#fafafa"
            />

            <path
              d="M22 0H0V22"
              fill="none"
              stroke="#e5e7eb"
              strokeWidth="0.7"
            />
          </pattern>

          <pattern
            id="wood-floor"
            width="42"
            height="12"
            patternUnits="userSpaceOnUse"
          >
            <rect
              width="42"
              height="12"
              fill="#eee7dc"
            />

            <line
              x1="0"
              y1="11"
              x2="42"
              y2="11"
              stroke="#d6c8b5"
            />
          </pattern>

          <pattern
            id="bath-tiles"
            width="18"
            height="18"
            patternUnits="userSpaceOnUse"
          >
            <rect
              width="18"
              height="18"
              fill="#dce1e5"
            />

            <path
              d="M18 0H0V18"
              fill="none"
              stroke="#bdc5cb"
              strokeWidth="0.7"
            />
          </pattern>

          <pattern
            id="kitchen-tiles"
            width="16"
            height="16"
            patternUnits="userSpaceOnUse"
          >
            <rect
              width="16"
              height="16"
              fill="#f1ede5"
            />

            <path
              d="M16 0H0V16"
              fill="none"
              stroke="#d4cabd"
              strokeWidth="0.7"
            />
          </pattern>
        </defs>

        {/* Drawing sheet */}

        <rect
          x="8"
          y="8"
          width={sheetWidth - 16}
          height={sheetHeight - 16}
          fill="#ffffff"
          stroke="#374151"
          strokeWidth="2"
        />

        {/* Project heading */}

        <text
          x={
            drawingAreaX +
            drawingAreaWidth / 2
          }
          y="48"
          textAnchor="middle"
          fontSize="28"
          fontWeight="700"
          fill="#111827"
        >
          {projectName}
        </text>

        <text
          x={
            drawingAreaX +
            drawingAreaWidth / 2
          }
          y={preview ? 55 : 72}
          textAnchor="middle"
          fontSize={preview ? 16 : 12}
          fontWeight={preview ? "700" : "400"}
          fill="#4b5563"
        >
          {String(floorName).toUpperCase()}
        </text>

        {!preview && (
          <NorthArrow
            x={72}
            y={112}
          />
        )}

        {!preview && (
          <HorizontalDimension
            x1={planX}
            x2={
              planX +
              renderedPlanWidth
            }
            y={planY - 25}
            label={`${floorPlanWidth.toFixed(
              2
            )} ft`}
          />
        )}

        {!preview && (
          <VerticalDimension
            x={planX - 30}
            y1={planY}
            y2={
              planY +
              renderedPlanHeight
            }
            label={`${floorPlanHeight.toFixed(
              2
            )} ft`}
          />
        )}

        {/* Rooms */}

        {rooms.map((room) => {
          const x =
            planX +
            Number(room.x || 0) * scale;

          const y =
            planY +
            Number(room.y || 0) * scale;

          const width =
            Number(room.width || 0) *
            scale;

          const height =
            Number(room.height || 0) *
            scale;

          return (
            <Room
              key={room.id}
              room={room}
              x={x}
              y={y}
              width={width}
              height={height}
            />
          );
        })}

        {/* Furniture */}

        {furniture.map((item) => (
          <Furniture
            key={item.id}
            item={item}
            planX={planX}
            planY={planY}
            scale={scale}
          />
        ))}

        {/* Doors */}

        {doors.map((door) => (
          <Door
            key={door.id}
            door={door}
            planX={planX}
            planY={planY}
            scale={scale}
          />
        ))}

        {/* Windows */}

        {windows.map(
          (windowItem) => (
            <Window
              key={windowItem.id}
              windowItem={windowItem}
              planX={planX}
              planY={planY}
              scale={scale}
            />
          )
        )}

        {/* Exterior wall */}

        <rect
          x={planX}
          y={planY}
          width={renderedPlanWidth}
          height={renderedPlanHeight}
          fill="none"
          stroke="#202020"
          strokeWidth="9"
          pointerEvents="none"
        />

        {!preview && (
          <TitlePanel
            x={940}
            y={32}
            width={240}
            height={716}
            floorPlan={floorPlan}
            project={project}
          />
        )}
      </svg>
    </div>
  );
}

function Room({
  room,
  x,
  y,
  width,
  height,
}) {
  let fill = "url(#floor-grid)";

  if (room.type === "bedroom") {
    fill = "url(#wood-floor)";
  }

  if (
    room.type === "bathroom" ||
    room.type === "utility"
  ) {
    fill = "url(#bath-tiles)";
  }

  if (room.type === "kitchen") {
    fill = "url(#kitchen-tiles)";
  }

  const area = Number(
    room.area ??
      Number(room.width || 0) *
        Number(room.height || 0)
  ).toFixed(1);

  const roomName = String(
    room.name ||
      room.type ||
      "Room"
  ).toUpperCase();

  const showArea =
    width >= 70 && height >= 42;

  const showLabel =
    width >= 42 && height >= 28;

  const labelWidth = Math.min(
    Math.max(width - 12, 70),
    150
  );

  const labelY =
    y +
    Math.max(
      18,
      Math.min(
        height - 18,
        height * 0.75
      )
    );

  return (
    <g>
      <rect
        x={x}
        y={y}
        width={Math.max(width, 0)}
        height={Math.max(height, 0)}
        fill={fill}
        stroke="#303030"
        strokeWidth="5"
      />

      {showLabel && (
        <g
          transform={`translate(${
            x + width / 2
          } ${labelY})`}
        >
          <rect
            x={-labelWidth / 2}
            y={showArea ? -18 : -12}
            width={labelWidth}
            height={showArea ? 36 : 24}
            rx="4"
            fill="#ffffff"
            fillOpacity="0.84"
          />

          <text
            x="0"
            y={showArea ? -3 : 4}
            textAnchor="middle"
            fontSize={Math.max(
              8,
              Math.min(
                14,
                width / 11
              )
            )}
            fontWeight="700"
            fill="#111827"
          >
            {roomName}
          </text>

          {showArea && (
            <text
              x="0"
              y="12"
              textAnchor="middle"
              fontSize="9"
              fill="#4b5563"
            >
              {area} sq ft
            </text>
          )}
        </g>
      )}
    </g>
  );
}

function Door({
  door,
  planX,
  planY,
  scale,
}) {
  const x =
    planX +
    Number(door.x || 0) * scale;

  const y =
    planY +
    Number(door.y || 0) * scale;

  const width = Math.max(
    Number(door.width || 0) *
      scale,
    2
  );

  const height = Math.max(
    Number(door.height || 0) *
      scale,
    2
  );

  const isHorizontal =
    door.orientation === "horizontal";

  const isMain =
    door.type === "main";

  const doorStrokeWidth = isMain
    ? 2.8
    : 2.1;

  if (isHorizontal) {
    const centreY =
      y + height / 2;

    const hingeX = x;
    const hingeY = centreY;

    const swingRadius = width;

    return (
      <g>
        <line
          x1={x}
          y1={centreY}
          x2={x + width}
          y2={centreY}
          stroke="#ffffff"
          strokeWidth="11"
        />

        <line
          x1={hingeX}
          y1={hingeY}
          x2={hingeX}
          y2={hingeY - swingRadius}
          stroke="#262626"
          strokeWidth={doorStrokeWidth}
        />

        <path
          d={[
            `M ${hingeX + swingRadius} ${hingeY}`,
            `A ${swingRadius} ${swingRadius}`,
            "0 0 0",
            `${hingeX} ${
              hingeY - swingRadius
            }`,
          ].join(" ")}
          fill="none"
          stroke="#6b7280"
          strokeWidth="1.2"
          strokeDasharray="3 2"
        />

        <circle
          cx={hingeX}
          cy={hingeY}
          r={isMain ? 2.5 : 2}
          fill="#262626"
        />
      </g>
    );
  }

  const centreX =
    x + width / 2;

  const hingeX = centreX;
  const hingeY = y;

  const swingRadius = height;

  return (
    <g>
      <line
        x1={centreX}
        y1={y}
        x2={centreX}
        y2={y + height}
        stroke="#ffffff"
        strokeWidth="11"
      />

      <line
        x1={hingeX}
        y1={hingeY}
        x2={hingeX + swingRadius}
        y2={hingeY}
        stroke="#262626"
        strokeWidth={doorStrokeWidth}
      />

      <path
        d={[
          `M ${hingeX} ${
            hingeY + swingRadius
          }`,
          `A ${swingRadius} ${swingRadius}`,
          "0 0 1",
          `${hingeX + swingRadius} ${hingeY}`,
        ].join(" ")}
        fill="none"
        stroke="#6b7280"
        strokeWidth="1.2"
        strokeDasharray="3 2"
      />

      <circle
        cx={hingeX}
        cy={hingeY}
        r={isMain ? 2.5 : 2}
        fill="#262626"
      />
    </g>
  );
}

function Window({
  windowItem,
  planX,
  planY,
  scale,
}) {
  const x =
    planX +
    Number(windowItem.x || 0) *
      scale;

  const y =
    planY +
    Number(windowItem.y || 0) *
      scale;

  const width = Math.max(
    Number(windowItem.width || 0) *
      scale,
    2
  );

  const height = Math.max(
    Number(windowItem.height || 0) *
      scale,
    2
  );

  const isHorizontal =
    windowItem.orientation ===
    "horizontal";

  if (isHorizontal) {
    const centreY =
      y + height / 2;

    return (
      <g>
        <line
          x1={x}
          y1={centreY}
          x2={x + width}
          y2={centreY}
          stroke="#ffffff"
          strokeWidth="11"
        />

        <line
          x1={x}
          y1={centreY - 3}
          x2={x + width}
          y2={centreY - 3}
          stroke="#2563eb"
          strokeWidth="2"
        />

        <line
          x1={x}
          y1={centreY + 3}
          x2={x + width}
          y2={centreY + 3}
          stroke="#2563eb"
          strokeWidth="2"
        />

        <line
          x1={x + width / 2}
          y1={centreY - 3}
          x2={x + width / 2}
          y2={centreY + 3}
          stroke="#2563eb"
          strokeWidth="1.4"
        />
      </g>
    );
  }

  const centreX =
    x + width / 2;

  return (
    <g>
      <line
        x1={centreX}
        y1={y}
        x2={centreX}
        y2={y + height}
        stroke="#ffffff"
        strokeWidth="11"
      />

      <line
        x1={centreX - 3}
        y1={y}
        x2={centreX - 3}
        y2={y + height}
        stroke="#2563eb"
        strokeWidth="2"
      />

      <line
        x1={centreX + 3}
        y1={y}
        x2={centreX + 3}
        y2={y + height}
        stroke="#2563eb"
        strokeWidth="2"
      />

      <line
        x1={centreX - 3}
        y1={y + height / 2}
        x2={centreX + 3}
        y2={y + height / 2}
        stroke="#2563eb"
        strokeWidth="1.4"
      />
    </g>
  );
}

function Furniture({
  item,
  planX,
  planY,
  scale,
}) {
  const x =
    planX +
    Number(item.x || 0) * scale;

  const y =
    planY +
    Number(item.y || 0) * scale;

  const width =
    Number(item.width || 0) * scale;

  const height =
    Number(item.height || 0) * scale;

  if (
    width <= 0 ||
    height <= 0
  ) {
    return null;
  }

  if (item.type === "bed") {
    return (
      <g>
        <rect
          x={x}
          y={y}
          width={width}
          height={height}
          rx="4"
          fill="#e7dfd3"
          stroke="#666"
          strokeWidth="1.4"
        />

        <line
          x1={x}
          y1={y}
          x2={x + width}
          y2={y}
          stroke="#555"
          strokeWidth="4"
        />

        <rect
          x={x + width * 0.07}
          y={y + height * 0.07}
          width={width * 0.35}
          height={height * 0.17}
          rx="7"
          fill="#fafafa"
          stroke="#777"
        />

        <rect
          x={x + width * 0.58}
          y={y + height * 0.07}
          width={width * 0.35}
          height={height * 0.17}
          rx="7"
          fill="#fafafa"
          stroke="#777"
        />

        <line
          x1={x}
          y1={y + height * 0.45}
          x2={x + width}
          y2={y + height * 0.45}
          stroke="#b4aa9e"
        />
      </g>
    );
  }

  if (item.type === "wardrobe") {
    return (
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        fill="#c6a679"
        stroke="#666"
      />
    );
  }

  if (item.type === "sofa") {
    return (
      <g>
        <rect
          x={x}
          y={y}
          width={width}
          height={height}
          rx="8"
          fill="#ddd3c6"
          stroke="#666"
        />

        <line
          x1={x + width / 3}
          y1={y}
          x2={x + width / 3}
          y2={y + height}
          stroke="#888"
        />

        <line
          x1={
            x +
            (width / 3) * 2
          }
          y1={y}
          x2={
            x +
            (width / 3) * 2
          }
          y2={y + height}
          stroke="#888"
        />
      </g>
    );
  }

  if (
    item.type === "coffee-table"
  ) {
    return (
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        rx="4"
        fill="#d7c7b3"
        stroke="#666"
      />
    );
  }

  if (item.type === "tv") {
    return (
      <rect
        x={x}
        y={y}
        width={Math.max(width, 6)}
        height={height}
        fill="#424242"
      />
    );
  }

  if (item.type === "counter") {
    return (
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        fill="#d9d2c7"
        stroke="#666"
      />
    );
  }

  if (item.type === "sink") {
    return (
      <g>
        <rect
          x={x}
          y={y}
          width={width}
          height={height}
          rx="4"
          fill="#fafafa"
          stroke="#666"
        />

        <circle
          cx={x + width / 2}
          cy={y + height / 2}
          r={
            Math.min(
              width,
              height
            ) * 0.25
          }
          fill="none"
          stroke="#666"
        />
      </g>
    );
  }

  if (
    item.type === "dining-table"
  ) {
    return (
      <g>
        <rect
          x={x}
          y={y}
          width={width}
          height={height}
          fill="#e4ddd4"
          stroke="#666"
        />

        {[0.15, 0.4, 0.65, 0.9].map(
          (position) => (
            <circle
              key={`top-${position}`}
              cx={
                x +
                width * position
              }
              cy={y - 8}
              r="7"
              fill="#eee7df"
              stroke="#666"
            />
          )
        )}

        {[0.15, 0.4, 0.65, 0.9].map(
          (position) => (
            <circle
              key={`bottom-${position}`}
              cx={
                x +
                width * position
              }
              cy={y + height + 8}
              r="7"
              fill="#eee7df"
              stroke="#666"
            />
          )
        )}
      </g>
    );
  }

  if (item.type === "bathtub") {
    return (
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        rx={
          Math.min(
            width,
            height
          ) * 0.35
        }
        fill="#fafafa"
        stroke="#666"
      />
    );
  }

  if (item.type === "toilet") {
    return (
      <ellipse
        cx={x + width / 2}
        cy={y + height / 2}
        rx={width / 2}
        ry={height / 2}
        fill="#fafafa"
        stroke="#666"
      />
    );
  }

  if (item.type === "basin") {
    return (
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        rx="5"
        fill="#fafafa"
        stroke="#666"
      />
    );
  }

  if (item.type === "washer") {
    return (
      <g>
        <rect
          x={x}
          y={y}
          width={width}
          height={height}
          fill="#fafafa"
          stroke="#666"
        />

        <circle
          cx={x + width / 2}
          cy={y + height / 2}
          r={
            Math.min(
              width,
              height
            ) * 0.3
          }
          fill="none"
          stroke="#666"
          strokeWidth="2"
        />
      </g>
    );
  }

  if (item.type === "storage") {
    return (
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        fill="#6b7280"
        stroke="#444"
      />
    );
  }

  return null;
}

function NorthArrow({
  x,
  y,
}) {
  return (
    <g
      transform={`translate(${x} ${y})`}
    >
      <text
        x="0"
        y="-42"
        textAnchor="middle"
        fontSize="18"
        fontWeight="700"
      >
        N
      </text>

      <circle
        cx="0"
        cy="0"
        r="29"
        fill="none"
        stroke="#111827"
      />

      <line
        x1="-39"
        y1="0"
        x2="39"
        y2="0"
        stroke="#111827"
      />

      <path
        d="M0 -39L9 9L0 3L-9 9Z"
        fill="#111827"
      />

      <path
        d="M0 39L-7 -7L0 -3L7 -7Z"
        fill="#ffffff"
        stroke="#111827"
      />
    </g>
  );
}

function HorizontalDimension({
  x1,
  x2,
  y,
  label,
}) {
  return (
    <g>
      <line
        x1={x1}
        y1={y}
        x2={x2}
        y2={y}
        stroke="#374151"
      />

      <line
        x1={x1}
        y1={y - 7}
        x2={x1}
        y2={y + 7}
        stroke="#374151"
      />

      <line
        x1={x2}
        y1={y - 7}
        x2={x2}
        y2={y + 7}
        stroke="#374151"
      />

      <circle
        cx={x1}
        cy={y}
        r="2.5"
      />

      <circle
        cx={x2}
        cy={y}
        r="2.5"
      />

      <text
        x={(x1 + x2) / 2}
        y={y - 8}
        textAnchor="middle"
        fontSize="13"
      >
        {label}
      </text>
    </g>
  );
}

function VerticalDimension({
  x,
  y1,
  y2,
  label,
}) {
  const middleY =
    (y1 + y2) / 2;

  return (
    <g>
      <line
        x1={x}
        y1={y1}
        x2={x}
        y2={y2}
        stroke="#374151"
      />

      <line
        x1={x - 7}
        y1={y1}
        x2={x + 7}
        y2={y1}
        stroke="#374151"
      />

      <line
        x1={x - 7}
        y1={y2}
        x2={x + 7}
        y2={y2}
        stroke="#374151"
      />

      <text
        x={x - 13}
        y={middleY}
        textAnchor="middle"
        fontSize="13"
        transform={`rotate(-90 ${
          x - 13
        } ${middleY})`}
      >
        {label}
      </text>
    </g>
  );
}

function TitlePanel({
  x,
  y,
  width,
  height,
  floorPlan,
  project,
}) {
  const rooms = Array.isArray(
    floorPlan.rooms
  )
    ? floorPlan.rooms
    : [];

  const floorPlanWidth = Number(
    floorPlan.width || 0
  );

  const floorPlanHeight = Number(
    floorPlan.height || 0
  );

  const totalArea = (
    floorPlanWidth *
    floorPlanHeight
  ).toFixed(1);

  const roomRowHeight = 22;

  const roomScheduleStart = 112;

  const roomScheduleEnd =
    roomScheduleStart +
    rooms.length * roomRowHeight;

  const summaryLineY = Math.max(
    340,
    roomScheduleEnd + 18
  );

  const requestedFloors =
    project?.floors ||
    project?.numberOfFloors ||
    floorPlan?.floors ||
    1;

  return (
    <g
      transform={`translate(${x} ${y})`}
    >
      <rect
        width={width}
        height={height}
        fill="#ffffff"
        stroke="#374151"
        strokeWidth="1.5"
      />

      <text
        x="16"
        y="36"
        fontSize="19"
        fontWeight="700"
      >
        ARCHITECTURAL FLOOR PLAN
      </text>

      <line
        x1="14"
        y1="52"
        x2={width - 14}
        y2="52"
        stroke="#4b5563"
      />

      <text
        x="16"
        y="84"
        fontSize="15"
        fontWeight="700"
      >
        ROOM SCHEDULE
      </text>

      {rooms.map(
        (room, index) => (
          <g key={room.id}>
            <text
              x="16"
              y={
                roomScheduleStart +
                index *
                  roomRowHeight
              }
              fontSize="10"
            >
              {index + 1}.{" "}
              {room.name ||
                room.type ||
                "Room"}
            </text>

            <text
              x={width - 16}
              y={
                roomScheduleStart +
                index *
                  roomRowHeight
              }
              textAnchor="end"
              fontSize="9"
            >
              {Number(
                room.width || 0
              ).toFixed(1)}
              {" × "}
              {Number(
                room.height || 0
              ).toFixed(1)}
            </text>
          </g>
        )
      )}

      <line
        x1="14"
        y1={summaryLineY}
        x2={width - 14}
        y2={summaryLineY}
        stroke="#4b5563"
      />

      <text
        x="16"
        y={summaryLineY + 30}
        fontSize="15"
        fontWeight="700"
      >
        AREA SUMMARY
      </text>

      <text
        x="16"
        y={summaryLineY + 62}
        fontSize="12"
      >
        Building area
      </text>

      <text
        x={width - 16}
        y={summaryLineY + 62}
        textAnchor="end"
        fontSize="12"
        fontWeight="700"
      >
        {totalArea} sq ft
      </text>

      <text
        x="16"
        y={summaryLineY + 92}
        fontSize="12"
      >
        Building size
      </text>

      <text
        x={width - 16}
        y={summaryLineY + 92}
        textAnchor="end"
        fontSize="12"
      >
        {floorPlanWidth.toFixed(1)}
        {" × "}
        {floorPlanHeight.toFixed(1)}
        {" ft"}
      </text>

      <text
        x="16"
        y={summaryLineY + 122}
        fontSize="12"
      >
        Match score
      </text>

      <text
        x={width - 16}
        y={summaryLineY + 122}
        textAnchor="end"
        fontSize="12"
      >
        {Number(
          floorPlan.match_score || 0
        ).toFixed(2)}
      </text>

      <text
        x="16"
        y={summaryLineY + 152}
        fontSize="12"
      >
        Rotation
      </text>

      <text
        x={width - 16}
        y={summaryLineY + 152}
        textAnchor="end"
        fontSize="12"
      >
        {Number(
          floorPlan.rotation || 0
        )}
        °
      </text>

      <line
        x1="14"
        y1={summaryLineY + 174}
        x2={width - 14}
        y2={summaryLineY + 174}
        stroke="#4b5563"
      />

      <text
        x="16"
        y={summaryLineY + 204}
        fontSize="15"
        fontWeight="700"
      >
        NOTES
      </text>

      <text
        x="16"
        y={summaryLineY + 230}
        fontSize="10"
      >
        • Dimensions are approximate.
      </text>

      <text
        x="16"
        y={summaryLineY + 253}
        fontSize="10"
      >
        • AI-generated conceptual layout.
      </text>

      <text
        x="16"
        y={summaryLineY + 276}
        fontSize="10"
      >
        • Verify with a licensed architect.
      </text>

      <line
        x1="14"
        y1={height - 86}
        x2={width - 14}
        y2={height - 86}
        stroke="#4b5563"
      />

      <text
        x="16"
        y={height - 48}
        fontSize="28"
        fontWeight="800"
      >
        ZYNORA
      </text>

      <text
        x="16"
        y={height - 27}
        fontSize="9"
        letterSpacing="2"
      >
        DESIGN YOUR DREAM SPACE
      </text>

      <text
        x={width - 16}
        y={height - 48}
        textAnchor="end"
        fontSize="10"
      >
        {requestedFloors} FLOOR
      </text>
    </g>
  );
}

export default FloorPlanCanvas;