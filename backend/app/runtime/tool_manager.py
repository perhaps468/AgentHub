"""Tool dictionary for the agent."""

from loguru import logger
from pydantic import BaseModel

from app.runtime.tools.tool import Tool


class ToolManager(BaseModel):
    """Tool dictionary for the agent."""

    tools: dict[str, Tool] = {}

    def tool_names(self) -> list[str]:
        """Get the names of all tools in the tool dictionary."""
        logger.debug("Getting tool names")
        return list(self.tools.keys())

    def add(self, tool: Tool):
        """Add a tool to the tool dictionary."""
        logger.debug(f"Adding tool: {tool.name} to tool dictionary")
        self.tools[tool.name] = tool

    def add_list(self, tools: list[Tool]):
        """Add a list of tools to the tool dictionary."""
        logger.debug(f"Adding {len(tools)} tools to tool dictionary")
        for tool in tools:
            self.add(tool)

    def remove(self, tool_name: str) -> bool:
        """Remove a tool from the tool dictionary."""
        logger.debug(f"Removing tool: {tool_name} from tool dictionary")
        del self.tools[tool_name]
        return True

    def get(self, tool_name: str) -> Tool | None:
        """Get a tool from the tool dictionary. Returns None if tool is not found."""
        logger.debug(f"Getting tool: {tool_name} from tool dictionary")
        return self.tools.get(tool_name)

    def list(self):
        """List all tools in the tool dictionary."""
        logger.debug("Listing all tools")
        return list(self.tools.keys())

    def execute(self, tool_name: str, **kwargs) -> str:
        """Execute a tool from the tool dictionary."""
        logger.debug(f"Executing tool: {tool_name} with arguments: {kwargs}")
        try:
            result = self.tools[tool_name].execute(**kwargs)
            logger.debug(f"Tool {tool_name} execution completed successfully")
            return result
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {str(e)}")
            raise

    def to_markdown(self):
        """Create a comprehensive Markdown representation of the tool dictionary."""
        logger.debug("Creating Markdown representation of tool dictionary")
        markdown = ""
        index: int = 1
        for tool_name, tool in self.tools.items():
            markdown += f"### {index}. {tool_name}\n"
            markdown += tool.to_markdown()
            markdown += "\n"
            index += 1
        return markdown

    def to_prompt_markdown(self, max_description_chars: int = 160):
        """Create a compact tool summary suitable for system prompts."""
        lines = []
        for index, (tool_name, tool) in enumerate(self.tools.items(), start=1):
            description = " ".join(str(getattr(tool, "description", "")).split())
            if len(description) > max_description_chars:
                description = description[: max_description_chars - 14].rstrip() + " ...[trimmed]"

            parameter_names = []
            for arg in getattr(tool, "arguments", []):
                if tool._is_internal_injectable(arg):
                    continue
                suffix = "*" if arg.required else ""
                parameter_names.append(f"{arg.name}{suffix}")

            params = f" ({', '.join(parameter_names)})" if parameter_names else ""
            lines.append(f"{index}. {tool_name}{params}: {description}".rstrip())
        return "\n".join(lines)

    def validate_and_convert_arguments(self, tool_name: str, provided_args: dict) -> dict:
        """Validates and converts arguments based on tool definition.

        T6: workspace_root is not required from the model — it's injected
        internally via get_injectable_properties_in_execution().
        """
        tool = self.get(tool_name)
        if tool is None:
            raise KeyError(f"Tool '{tool_name}' not found")
        converted_args = {}
        type_conversion = {
            "string": lambda x: str(x),
            "int": lambda x: int(x),
            "float": lambda x: float(x),
            "bool": lambda x: str(x).lower() in ("true", "1", "yes"),
        }

        all_arg_names = {arg_def.name for arg_def in tool.arguments}

        for arg_def in tool.arguments:
            arg_name = arg_def.name
            arg_type = arg_def.arg_type
            required = arg_def.required
            default = getattr(arg_def, "default", None)

            # T6: workspace_root is injected internally, skip required check
            if tool._is_internal_injectable(arg_def):
                continue

            if arg_name not in provided_args:
                if required:
                    raise ValueError(f"Missing required argument: {arg_name}")
                if default is None:
                    continue
                # Set default in a working dict (not mutating provided_args)
                if arg_type in type_conversion:
                    try:
                        converted_args[arg_name] = type_conversion[arg_type](default)
                    except (ValueError, TypeError):
                        converted_args[arg_name] = default
                else:
                    converted_args[arg_name] = default
                continue

            value = provided_args[arg_name]

            # Treat empty strings as "not provided" — fall back to default
            if isinstance(value, str) and not value.strip():
                if required:
                    raise ValueError(f"Missing required argument: {arg_name}")
                if default is None:
                    continue
                if arg_type in type_conversion:
                    try:
                        converted_args[arg_name] = type_conversion[arg_type](default)
                    except (ValueError, TypeError):
                        converted_args[arg_name] = default
                else:
                    converted_args[arg_name] = default
                continue

            if arg_type in type_conversion:
                try:
                    converted = type_conversion[arg_type](value)
                except (ValueError, TypeError) as e:
                    raise ValueError(f"Invalid value '{value}' for {arg_name} ({arg_type}): {str(e)}")
                converted_args[arg_name] = converted
            else:
                converted_args[arg_name] = value

        # T6: model might accidentally pass workspace_root; filter it out
        injectable_names = {"variables", "caller_context_memory", "workspace_root"}
        extra_args = set(provided_args.keys()) - all_arg_names - injectable_names
        if extra_args:
            raise ValueError(f"Unexpected arguments: {', '.join(extra_args)}")

        # T6: inject internal properties (e.g. workspace_root) after validation
        injectable_props = tool.get_injectable_properties_in_execution()
        converted_args.update(injectable_props)

        return converted_args
