import React from "react";
import { Composition, registerRoot } from "remotion";
import { Film, filmMeta } from "./Film";
import { SEED_PROJECT } from "./seed";

function Root() {
  return <Composition id="Film" component={Film} defaultProps={{ project: SEED_PROJECT }} {...filmMeta(SEED_PROJECT)}
    calculateMetadata={({ props }) => filmMeta(props.project)} />;
}

registerRoot(Root);
