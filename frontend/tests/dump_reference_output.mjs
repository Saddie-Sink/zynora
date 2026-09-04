// Diagnostic-only harness (NOT part of the app or its test suite).
// Dumps processWallTopology/createFloorPlanDocument output as JSON so it
// can be diffed against the new Python canonical_builder for the P0
// equivalence check. Safe to delete after the check is complete.

import {
  createFloorPlanDocument,
  processWallTopology,
  validateFloorPlanGeometry,
} from "../src/components/viewerV2/utils/wallTopology.js";

function wall(id, x1, z1, x2, z2, options = {}) {
  return {
    id,
    x1,
    z1,
    x2,
    z2,
    height: 2.8,
    thickness: 0.16,
    color: "#eee9e1",
    isExterior: true,
    openings: [],
    ...options,
  };
}

const outline = [
  { x: 0, z: 0 },
  { x: 10, z: 0 },
  { x: 10, z: 7 },
  { x: 0, z: 7 },
];

// Fixture A: duplicate/collinear wall merge + opening preservation
// (same fixture as the existing "merges duplicate walls..." unit test)
const topologyA = processWallTopology({
  outline,
  walls: [
    wall("south", 0, 0, 10, 0, {
      openings: [
        {
          id: "front-door",
          type: "door",
          start: 4.5,
          end: 5.5,
          center: 5,
          width: 1,
          bottom: 0,
          top: 2.1,
          height: 2.1,
        },
      ],
    }),
    wall("south-copy", 0.001, 0.001, 10.001, 0.001),
    wall("east", 10, 0, 10, 7),
    wall("north", 10, 7, 0, 7),
    wall("west", 0, 7, 0, 0),
  ],
});

// Fixture B: canonical FloorPlanJSON for a simple closed shell
// (same fixture as the existing "creates valid canonical FloorPlanJSON..." test)
const topologyB = processWallTopology({
  outline,
  walls: [
    wall("south", 0, 0, 10, 0),
    wall("east", 10, 0, 10, 7),
    wall("north", 10, 7, 0, 7),
    wall("west", 0, 7, 0, 0),
  ],
});
const planB = {
  id: "test-plan",
  floorId: "ground-floor",
  floorIndex: 0,
  floorCount: 1,
  sourceType: "unit-test",
  classifierVersion: "v5",
  height: 2.8,
  outline: topologyB.exteriorOutline,
  exteriorOutline: topologyB.exteriorOutline,
  rooms: [],
  walls: topologyB.walls,
  shellWalls: topologyB.shellWalls,
  slab: { elevation: -0.16, thickness: 0.18 },
  roof: {
    type: "flat",
    elevation: 2.8,
    thickness: 0.22,
    parapetHeight: 0.35,
  },
};
const validationB = validateFloorPlanGeometry(planB);
const documentB = createFloorPlanDocument(planB, validationB);

console.log(
  JSON.stringify(
    {
      fixtureA: { stats: topologyA.stats, walls: topologyA.walls },
      fixtureB: { validation: validationB, document: documentB },
    },
    null,
    2,
  ),
);
