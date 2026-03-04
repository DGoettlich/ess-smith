from swesmith.bug_gen.procedural.base import ProceduralModifier
from swesmith.bug_gen.procedural.r.control_flow import (
    ControlIfElseInvertModifier,
    ControlShuffleLinesModifier,
)
from swesmith.bug_gen.procedural.r.operations import (
    OperationBreakChainsModifier,
    OperationChangeConstantsModifier,
    OperationChangeModifier,
    OperationFlipOperatorModifier,
    OperationSwapOperandsModifier,
)
from swesmith.bug_gen.procedural.r.remove import (
    RemoveAssignModifier,
    RemoveConditionalModifier,
    RemoveLoopModifier,
)

MODIFIERS_R: list[ProceduralModifier] = [
    ControlIfElseInvertModifier(likelihood=0.75),
    ControlShuffleLinesModifier(likelihood=0.75),
    RemoveAssignModifier(likelihood=0.25),
    RemoveConditionalModifier(likelihood=0.25),
    RemoveLoopModifier(likelihood=0.25),
    OperationBreakChainsModifier(likelihood=0.4),
    OperationChangeConstantsModifier(likelihood=0.4),
    OperationChangeModifier(likelihood=0.4),
    OperationFlipOperatorModifier(likelihood=0.4),
    OperationSwapOperandsModifier(likelihood=0.4),
]
