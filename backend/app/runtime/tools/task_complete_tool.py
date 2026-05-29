"""Tool for replying answer to the user."""

from app.runtime.tools.tool import Tool, ToolArgument


class TaskCompleteTool(Tool):
    """Tool to reply answer to the user."""

    name: str = "task_complete"
    description: str = "Replies to the user when the task is completed."
    arguments: list = [
        ToolArgument(
            name="answer",
            arg_type="string",
            description="The answer to the user. Use interpolation if possible example $var1$.",
            required=True,
            example="The answer to the meaning of life",
        ),
    ]

    def execute(self, answer: str) -> str:
        """Attempts to reply to the user.

        Args:
            answer: The answer to the user.

        Returns:
            The answer to the user.
        """
        return answer
