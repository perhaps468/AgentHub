"""Enhanced ReAct agent for AgentHub runtime.

B 类文件，从 quantalogic_react/quantalogic/agent.py 迁移，
最小改动：调整 import 路径从 quantalogic_react.quantalogic.* 到 app.runtime.*。
后续改造阶段由 02-implementation-guide.md 负责：
- 替换模型调用为 AgentHub Provider
- 裁剪 chat/多模态/非必须分支
- 统一事件语义
- 接入 WebSocket 主链路
"""

import asyncio
import os
import re
import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from jinja2 import Environment, FileSystemLoader
from loguru import logger
from pydantic import BaseModel, ConfigDict, PrivateAttr

from app.runtime.generative_model import GenerativeModel, ResponseStats, TokenUsage
from app.runtime.llm_wrapper import LLMWrapper
from app.runtime.memory import AgentMemory, Message, VariableMemory
from app.runtime.prompts import system_prompt
from app.runtime.tool_manager import ToolManager
from app.runtime.tools.task_complete_tool import TaskCompleteTool
from app.runtime.tools.tool import Tool
from app.runtime.utils import get_environment
from app.runtime.xml_parser import ToleranceXMLParser
from app.runtime.xml_tool_parser import ToolParser

MAX_OCCUPANCY = 90.0
MAX_RESPONSE_LENGTH = 1024 * 32
DEFAULT_MAX_INPUT_TOKENS = 128 * 1024
DEFAULT_MAX_OUTPUT_TOKENS = 4096
MAX_INTERPOLATION_DEPTH = 10
PROTOCOL_TAG_NAMES = (
    "thinking",
    "action",
    "context_analysis",
    "execution_analysis",
    "decision_matrix",
    "memory_pad",
    "task_complete",
)


class _NoopEventEmitter:
    """Minimal local placeholder until AgentHub defines a real runtime event bridge."""

    def emit(self, event: str, *args, **kwargs) -> None:
        logger.debug(f"[runtime noop event] {event}")


async def _deny_user_validation(validation_id: str, question: str) -> bool:
    """Compatibility fallback for copied Runtime code paths that request confirmation."""
    logger.debug(f"Ignoring runtime user validation request: {validation_id}")
    return False


class AgentConfig(BaseModel):
    """Configuration settings for the Agent."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    environment_details: str
    tools_markdown: str
    system_prompt: str


class ObserveResponseResult(BaseModel):
    """Represents the result of observing the assistant's response."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    next_prompt: str
    executed_tool: str | None = None
    answer: str | None = None
    tool_not_found: bool = False
    tool_execution_failed: bool = False


class Agent(BaseModel):
    """Enhanced ReAct agent supporting both goal-solving and conversational chat modes.

    B 类文件，从 quantalogic 迁移。
    后续由 02-implementation-guide.md 决定如何接入 AgentHub Provider / WS 链路。
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, validate_assignment=True, extra="forbid")

    specific_expertise: str
    memory: AgentMemory = AgentMemory()
    variable_store: VariableMemory = VariableMemory()
    tools: ToolManager = ToolManager()
    event_emitter: object = _NoopEventEmitter()
    config: AgentConfig
    task_to_solve: str
    task_to_solve_summary: str = ""
    ask_for_user_validation: Callable[[str, str], bool] = _deny_user_validation
    last_tool_call: dict[str, Any] = {}
    total_tokens: int = 0
    current_iteration: int = 0
    max_input_tokens: int = DEFAULT_MAX_INPUT_TOKENS
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS
    max_iterations: int = 30
    system_prompt: str = ""
    compact_every_n_iterations: int | None = None
    max_tokens_working_memory: int | None = None
    _model_name: str = PrivateAttr(default="")
    _llm_adapter: Any = PrivateAttr(default=None)
    _model_wrapper: Any = PrivateAttr(default=None)
    chat_system_prompt: str = ""
    tool_mode: Optional[str] = None
    tracked_files: list[str] = []
    agent_mode: str = "react"

    def __init__(
        self,
        model_name: str = "",
        llm_adapter=None,  # LLMAdapter instance (M3 canonical path)
        memory: AgentMemory = AgentMemory(),
        variable_store: VariableMemory = VariableMemory(),
        tools: list[Tool] = [TaskCompleteTool()],
        ask_for_user_validation: Callable[[str, str], bool] = _deny_user_validation,
        task_to_solve: str = "",
        specific_expertise: str = "General AI assistant with coding and problem-solving capabilities",
        get_environment: Callable[[], str] = get_environment,
        compact_every_n_iterations: int | None = None,
        max_tokens_working_memory: int | None = None,
        event_emitter: _NoopEventEmitter | None = None,
        chat_system_prompt: str | None = None,
        tool_mode: Optional[str] = None,
        agent_mode: str = "react",
        max_iterations: int = 30,
    ):
        """Initialize the agent with model, memory, tools, and configurations.

        M3: Pass llm_adapter to use the AgentHub Provider-backed LLM path.
        If llm_adapter is None, falls back to copied GenerativeModel (deprecated path).
        """
        try:
            logger.debug("Initializing agent...")

            if event_emitter is None:
                event_emitter = _NoopEventEmitter()

            if not any(isinstance(t, TaskCompleteTool) for t in tools):
                tools.append(TaskCompleteTool())

            tool_manager = ToolManager(tools={tool.name: tool for tool in tools})
            environment = get_environment()
            logger.debug(f"Environment details: {environment}")
            tools_markdown = tool_manager.to_markdown()
            logger.debug(f"Tools Markdown: {tools_markdown}")

            logger.info(f"Agent mode: {agent_mode}")
            system_prompt_text = system_prompt(
                tools=tools_markdown, environment=environment, expertise=specific_expertise, agent_mode=agent_mode
            )
            logger.debug(f"System prompt: {system_prompt_text}")

            config = AgentConfig(
                environment_details=environment,
                tools_markdown=tools_markdown,
                system_prompt=system_prompt_text,
            )

            chat_system_prompt = chat_system_prompt or specific_expertise or (
                "You are a friendly, helpful AI assistant. Engage in natural conversation, "
                "answer questions, and use tools when explicitly requested or when they enhance your response."
            )

            # M3: When llm_adapter is provided, wrap it in LLMWrapper for
            # GenerativeModel-compatible interface. This is the canonical path.
            if llm_adapter is not None:
                model = LLMWrapper(llm_adapter=llm_adapter, model_name=model_name, event_emitter=event_emitter)
            else:
                model = GenerativeModel(model=model_name, event_emitter=event_emitter)

            super().__init__(
                specific_expertise=specific_expertise,
                memory=memory,
                variable_store=variable_store,
                tools=tool_manager,
                event_emitter=event_emitter,
                config=config,
                task_to_solve=task_to_solve,
                task_to_solve_summary="",
                ask_for_user_validation=ask_for_user_validation,
                last_tool_call={},
                total_tokens=0,
                current_iteration=0,
                max_input_tokens=DEFAULT_MAX_INPUT_TOKENS,
                max_output_tokens=DEFAULT_MAX_OUTPUT_TOKENS,
                max_iterations=max_iterations,
                system_prompt="",
                compact_every_n_iterations=compact_every_n_iterations or 30,
                max_tokens_working_memory=max_tokens_working_memory,
                chat_system_prompt=chat_system_prompt,
                tool_mode=tool_mode,
                agent_mode=agent_mode,
            )

            self._model_name = model_name
            self._llm_adapter = llm_adapter
            # M3: Store the wrapped model. When llm_adapter is provided,
            # this is a LLMWrapper. Otherwise, wraps the copied GenerativeModel.
            if llm_adapter is not None:
                self._model_wrapper = LLMWrapper(llm_adapter=llm_adapter, model_name=model_name, event_emitter=event_emitter)
            else:
                self._model_wrapper = GenerativeModel(model=model_name, event_emitter=event_emitter)

            logger.debug(f"Memory will be compacted every {self.compact_every_n_iterations} iterations")
            logger.debug(f"Max tokens for working memory set to: {self.max_tokens_working_memory}")
            logger.debug(f"Tool mode set to: {self.tool_mode}")
            logger.debug("Agent initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize agent: {str(e)}")
            raise

    @property
    def model_name(self) -> str:
        """Get the current model name."""
        return self._model_name

    @model_name.setter
    def model_name(self, value: str) -> None:
        """Set the model name and update the model wrapper instance."""
        self._model_name = value
        if self._llm_adapter is not None:
            self._model_wrapper = LLMWrapper(
                llm_adapter=self._llm_adapter, model_name=value, event_emitter=self.event_emitter
            )
        else:
            self._model_wrapper = GenerativeModel(model=value, event_emitter=self.event_emitter)

    @property
    def model(self):
        """Return the active model wrapper (LLMWrapper or GenerativeModel)."""
        return self._model_wrapper

    def clear_memory(self) -> None:
        """Clear the memory and reset the session."""
        self._reset_session(clear_memory=True)

    def solve_task(
        self, task: str, max_iterations: int = 30, streaming: bool = False, clear_memory: bool = True
    ) -> str:
        """Solve the given task using the ReAct framework (synchronous version)."""
        logger.debug(f"Solving task... {task}")
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.async_solve_task(task, max_iterations, streaming, clear_memory))

    async def async_solve_task(
        self, task: str, max_iterations: int = 30, streaming: bool = False, clear_memory: bool = True
    ) -> str:
        """Solve the given task using the ReAct framework (asynchronous version)."""
        logger.debug(f"Solving task asynchronously... {task}")
        self._reset_session(task_to_solve=task, max_iterations=max_iterations, clear_memory=clear_memory)
        self.task_to_solve_summary = await self._async_generate_task_summary(task)

        if not self.memory.memory or self.memory.memory[0].role != "system":
            self.memory.add(Message(role="system", content=self.config.system_prompt))

        self._emit_event("session_start", {"system_prompt": self.config.system_prompt, "content": task})

        self.max_output_tokens = self.model.get_model_max_output_tokens() or DEFAULT_MAX_OUTPUT_TOKENS
        self.max_input_tokens = self.model.get_model_max_input_tokens() or DEFAULT_MAX_INPUT_TOKENS

        done = False
        current_prompt = self._prepare_prompt_task(task)
        self.current_iteration = 1
        answer = ""

        while not done:
            try:
                self._update_total_tokens(self.memory.memory, current_prompt)
                self._emit_event("task_think_start", {"prompt": current_prompt})
                await self._async_compact_memory_if_needed(current_prompt)

                if streaming:
                    # T2: Real streaming: yield token-level deltas
                    full_response = ""
                    async for delta in self.model.async_stream_generate_with_history(
                        messages_history=self.memory.memory,
                        prompt=current_prompt,
                    ):
                        full_response += delta
                        self._emit_event("model_delta", {"delta": delta})
                    content = full_response
                    if self._is_low_signal_response(content):
                        logger.debug(
                            "Runtime streaming response classified as low_signal, "
                            "triggering non-streaming fallback [iteration={}]: {}",
                            self.current_iteration,
                            content[:200].replace("\n", "\\n"),
                        )
                        fallback_result = await self.model.async_generate_with_history(
                            messages_history=self.memory.memory,
                            prompt=current_prompt,
                            streaming=False,
                        )
                        fallback_content = fallback_result.response.strip()
                        if fallback_content:
                            content = fallback_content
                            token_usage = fallback_result.usage
                            self.total_tokens = token_usage.total_tokens
                        else:
                            self.total_tokens = self.model.token_counter_with_history(
                                self.memory.memory, full_response
                            )
                    elif self._is_incomplete_direct_reply(content):
                        logger.debug(
                            "Runtime streaming response classified as incomplete_direct_reply, "
                            "triggering non-streaming fallback [iteration={}]: {}",
                            self.current_iteration,
                            content[:200].replace("\n", "\\n"),
                        )
                        fallback_result = await self.model.async_generate_with_history(
                            messages_history=self.memory.memory,
                            prompt=current_prompt,
                            streaming=False,
                        )
                        fallback_content = fallback_result.response.strip()
                        if fallback_content:
                            content = fallback_content
                            token_usage = fallback_result.usage
                            self.total_tokens = token_usage.total_tokens
                        else:
                            self.total_tokens = self.model.token_counter_with_history(
                                self.memory.memory, full_response
                            )
                    else:
                        self.total_tokens = self.model.token_counter_with_history(
                            self.memory.memory, full_response
                        )
                else:
                    result = await self.model.async_generate_with_history(
                        messages_history=self.memory.memory,
                        prompt=current_prompt,
                        streaming=False,
                    )
                    content = result.response
                    token_usage = result.usage
                    self.total_tokens = token_usage.total_tokens

                logger.debug(
                    "Runtime model raw response preview (iteration={}): {}",
                    self.current_iteration,
                    content[:500].replace("\n", "\\n"),
                )

                self._emit_event("task_think_end", {"response": content})
                result = await self._async_observe_response(content, iteration=self.current_iteration)

                if result.tool_not_found:
                    self._emit_event("error_tool_not_found", {"tool": result.next_prompt})
                    self._update_session_memory(result.next_prompt, content)
                    answer = result.next_prompt
                    done = True
                elif result.executed_tool == "task_complete":
                    logger.debug(
                        "Runtime response classified as action_call: tool='task_complete' [iteration={}]",
                        self.current_iteration,
                    )
                    self._emit_event("task_complete", {
                        "response": result.answer,
                        "message": "Task execution completed",
                        "tracked_files": self.tracked_files if self.tracked_files else []
                    })
                    self._update_session_memory(result.next_prompt, content)
                    answer = result.answer or ""
                    done = True
                elif result.tool_execution_failed:
                    # Tool execution failed (e.g., validation denied) — emit error and terminate.
                    logger.debug(
                        "Runtime response: tool execution failed [iteration={}]: {}",
                        self.current_iteration,
                        result.next_prompt[:500].replace("\n", "\\n"),
                    )
                    self._emit_event("task_complete", {
                        "response": result.next_prompt,
                        "message": "Tool execution failed",
                        "tracked_files": self.tracked_files if self.tracked_files else []
                    })
                    self._update_session_memory(result.next_prompt, content)
                    answer = result.next_prompt
                    done = True
                elif result.executed_tool is None:
                    # No tool call detected — treat the response as the final answer.
                    # This is the natural termination for models that answer directly
                    # without invoking tools (direct reply first protocol).
                    logger.debug(
                        "Runtime response classified as direct_reply (no action) "
                        "[iteration={}]: {}",
                        self.current_iteration,
                        content[:500].replace("\n", "\\n"),
                    )
                    final_answer = result.next_prompt or content
                    normalized = self._normalize_final_answer(final_answer)
                    logger.debug(
                        "Runtime no-tool final answer preview (iteration={}): {}",
                        self.current_iteration,
                        normalized[:500].replace("\n", "\\n"),
                    )
                    self._emit_event("task_complete", {
                        "response": normalized,
                        "message": "Task execution completed (direct reply, no action)",
                        "tracked_files": self.tracked_files if self.tracked_files else []
                    })
                    self._update_session_memory(result.next_prompt, content)
                    answer = normalized
                    done = True
                else:
                    self._update_session_memory(result.next_prompt, content)
                    current_prompt = result.next_prompt
                    self.current_iteration += 1
                    if self.current_iteration >= self.max_iterations:
                        done = True
                        self._emit_event("error_max_iterations_reached")

                if done:
                    break

            except Exception as e:
                logger.error(f"Error during async task solving: {str(e)}")
                answer = f"Error: {str(e)}"
                done = True

        task_solve_end_data = {
            "result": answer,
            "message": "Task execution completed",
            "tracked_files": self.tracked_files if self.tracked_files else []
        }
        self._emit_event("task_solve_end", task_solve_end_data)
        return answer

    def chat(
        self,
        message: str,
        streaming: bool = False,
        clear_memory: bool = False,
        auto_tool_call: bool = True,
    ) -> str:
        """Engage in a conversational chat with the user (synchronous version)."""
        logger.debug(f"Chatting synchronously with message: {message}, auto_tool_call: {auto_tool_call}")
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.async_chat(message, streaming, clear_memory, auto_tool_call))

    async def async_chat(
        self,
        message: str,
        streaming: bool = False,
        clear_memory: bool = False,
        auto_tool_call: bool = True,
    ) -> str:
        """Engage in a conversational chat with the user (asynchronous version)."""
        logger.debug(f"Chatting asynchronously with message: {message}, auto_tool_call: {auto_tool_call}")
        if clear_memory:
            self.clear_memory()

        tools_prompt = self._get_tools_names_prompt()
        logger.debug(tools_prompt)
        if self.tool_mode:
            tools_prompt += f"\nPrioritized tool mode: {self.tool_mode}. Prefer tools related to {self.tool_mode} when applicable."

        full_chat_prompt = self._render_template(
            'chat_system_prompt.j2',
            persona=self.chat_system_prompt,
            tools_prompt=tools_prompt
        )

        if not self.memory.memory or self.memory.memory[0].role != "system":
            self.memory.add(Message(role="system", content=full_chat_prompt))

        self._emit_event("chat_start", {"message": message})

        self.memory.add(Message(role="user", content=message))
        self._update_total_tokens(self.memory.memory, "")

        current_prompt = message
        response_content = ""
        max_tool_iterations = 5
        tool_iteration = 0

        while tool_iteration < max_tool_iterations:
            try:
                response = await self.model.async_generate_with_history(
                    messages_history=self.memory.memory,
                    prompt=current_prompt,
                    streaming=False,
                )
                content = response.response
                self.total_tokens = response.usage.total_tokens

                observation = await self._async_observe_response(content)
                if observation.executed_tool and auto_tool_call:
                    current_prompt = observation.next_prompt

                    if not self.task_to_solve.strip():
                        response_content = f"{content}\n\n__TOOL_RESULT_SEPARATOR__{observation.executed_tool}__\n{observation.next_prompt}"
                    else:
                        response_content = observation.next_prompt

                    tool_iteration += 1
                    self.memory.add(Message(role="assistant", content=content))
                    self.memory.add(Message(role="user", content=observation.next_prompt))
                    logger.debug(f"Tool executed: {observation.executed_tool}, iteration: {tool_iteration}")
                elif not observation.executed_tool and "<action>" in content and auto_tool_call:
                    response_content = (
                        f"{content}\n\n⚠️ Error: Invalid tool call format detected. "
                        "Please use the exact XML structure as specified in the system prompt:\n"
                        "```xml\n<action>\n<tool_name>\n  <parameter_name>value</parameter_name>\n</tool_name>\n</action>\n```"
                    )
                    break
                else:
                    response_content = content
                    break

            except Exception as e:
                logger.error(f"Error during async chat: {str(e)}")
                response_content = f"Error: {str(e)}"
                break

        self._update_session_memory(message, response_content)
        self._emit_event("chat_response", {"response": response_content})
        return response_content

    def chat_news_specific(
        self,
        message: str,
        streaming: bool = False,
        clear_memory: bool = False,
        auto_tool_call: bool = True,
    ) -> str:
        """Engage in a conversational chat_news_specific with the user (synchronous version)."""
        logger.debug(f"chat_news_specificting synchronously with message: {message}, auto_tool_call: {auto_tool_call}")
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.async_chat_news_specific(message, streaming, clear_memory, auto_tool_call))

    async def async_chat_news_specific(
        self,
        message: str,
        streaming: bool = False,
        clear_memory: bool = False,
        auto_tool_call: bool = True,
    ) -> str:
        """Engage in a conversational chat with the user (asynchronous version)."""
        logger.debug(f"Chatting asynchronously with message: {message}, auto_tool_call: {auto_tool_call}")
        if clear_memory:
            self.clear_memory()

        tools_prompt = self._get_tools_names_prompt()
        logger.debug(tools_prompt)
        if self.tool_mode:
            tools_prompt += f"\nPrioritized tool mode: {self.tool_mode}. Prefer tools related to {self.tool_mode} when applicable."

        full_chat_prompt = self._render_template(
            'chat_system_prompt.j2',
            persona=self.chat_system_prompt,
            tools_prompt=tools_prompt
        )

        if not self.memory.memory or self.memory.memory[0].role != "system":
            self.memory.add(Message(role="system", content=full_chat_prompt))

        self._emit_event("chat_start", {"message": message})

        self.memory.add(Message(role="user", content=message))
        self._update_total_tokens(self.memory.memory, "")

        current_prompt = message
        response_content = ""
        max_tool_iterations = 5
        tool_iteration = 0

        while tool_iteration < max_tool_iterations:
            try:
                response = await self.model.async_generate_with_history(
                    messages_history=self.memory.memory,
                    prompt=current_prompt,
                    streaming=False,
                )
                content = response.response
                self.total_tokens = response.usage.total_tokens

                observation = await self._async_observe_response(content)
                if observation.executed_tool and auto_tool_call:
                    print("observation.executed_tool : ", observation.executed_tool)
                    if "googlenews" in observation.executed_tool.lower() or \
                       "duckduckgo" in observation.executed_tool.lower() or \
                       "duckduckgosearch" in observation.executed_tool.lower():
                        self._emit_event("chat_response", {"response": observation.next_prompt})
                        return observation.next_prompt

                    current_prompt = observation.next_prompt

                    if not self.task_to_solve.strip():
                        response_content = f"{content}\n\n__TOOL_RESULT_SEPARATOR__{observation.executed_tool}__\n{observation.next_prompt}"
                    else:
                        response_content = observation.next_prompt

                    tool_iteration += 1
                    self.memory.add(Message(role="assistant", content=content))
                    self.memory.add(Message(role="user", content=observation.next_prompt))
                    logger.debug(f"Tool executed: {observation.executed_tool}, iteration: {tool_iteration}")
                elif not observation.executed_tool and "<action>" in content and auto_tool_call:
                    response_content = (
                        f"{content}\n\n⚠️ Error: Invalid tool call format detected. "
                        "Please use the exact XML structure as specified in the system prompt:\n"
                        "```xml\n<action>\n<tool_name>\n  <parameter_name>value</parameter_name>\n</tool_name>\n</action>\n```"
                    )
                    break
                else:
                    response_content = content
                    break

            except Exception as e:
                logger.error(f"Error during async chat: {str(e)}")
                response_content = f"Error: {str(e)}"
                break

        self._update_session_memory(message, response_content)
        self._emit_event("chat_response", {"response": response_content})
        return response_content

    def _observe_response(self, content: str, iteration: int = 1) -> ObserveResponseResult:
        """Analyze the assistant's response and determine next steps (synchronous wrapper)."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self._async_observe_response(content, iteration))

    async def _async_observe_response(self, content: str, iteration: int = 1) -> ObserveResponseResult:
        """Analyze the assistant's response and determine next steps (asynchronous)."""
        try:
            is_chat_mode = not self.task_to_solve.strip()

            if is_chat_mode:
                return await self._async_observe_response_chat(content, iteration)

            parsed_content = self._parse_tool_usage(content)
            if not parsed_content:
                logger.debug(
                    "Runtime response classified as direct_reply (no action, no tool) [iteration={}]: {}",
                    iteration,
                    content[:500].replace("\n", "\\n"),
                )
                visible_content = self._normalize_final_answer(content)
                logger.debug(
                    "Normalized direct_reply response preview: {}",
                    visible_content[:500].replace("\n", "\\n"),
                )
                return ObserveResponseResult(next_prompt=visible_content, executed_tool=None, answer=None)

            tool_names = list(parsed_content.keys())
            for tool_name in tool_names:
                if tool_name not in parsed_content:
                    continue
                logger.debug(
                    "Runtime response classified as action_call: tool='{}' [iteration={}]",
                    tool_name,
                    iteration,
                )
                tool_input = parsed_content[tool_name]
                tool = self.tools.get(tool_name)
                if not tool:
                    return self._handle_tool_not_found(tool_name)

                arguments_with_values = self._parse_tool_arguments(tool, tool_input)
                is_repeated_call = self._is_repeated_tool_call(tool_name, arguments_with_values)

                if is_repeated_call:
                    executed_tool, response = self._handle_repeated_tool_call(tool_name, arguments_with_values)
                else:
                    executed_tool, response = await self._async_execute_tool(tool_name, tool, arguments_with_values)

                if not executed_tool:
                    return self._handle_tool_execution_failure(response)

                if (tool_name in ["write_file_tool", "writefile", "edit_whole_content", "replace_in_file", "replaceinfile", "EditWholeContent"]) and "file_path" in arguments_with_values:
                    self._track_file(arguments_with_values["file_path"], tool_name)

                variable_name = self.variable_store.add(response)
                new_prompt = self._format_observation_response(response, executed_tool, variable_name, iteration)

                is_task_complete_answer = executed_tool == "task_complete" and not is_chat_mode

                return ObserveResponseResult(
                    next_prompt=new_prompt,
                    executed_tool=executed_tool,
                    answer=response if is_task_complete_answer else None,
                )

            return ObserveResponseResult(
                next_prompt=self._normalize_final_answer(content),
                executed_tool=None,
                answer=None,
            )

        except Exception as e:
            return self._handle_error(e)

    def _execute_tool(self, tool_name: str, tool: Tool, arguments_with_values: dict) -> tuple[str, Any]:
        """Execute a tool with validation if required (synchronous wrapper)."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self._async_execute_tool(tool_name, tool, arguments_with_values))

    async def _async_execute_tool(self, tool_name: str, tool: Tool, arguments_with_values: dict) -> tuple[str, Any]:
        """Execute a tool with validation if required (asynchronous)."""
        if tool.need_validation:
            logger.info(f"Tool '{tool_name}' requires validation.")
            validation_id = str(uuid.uuid4())
            logger.info(f"Validation ID: {validation_id}")

            self._emit_event(
                "tool_execute_validation_start",
                {
                    "validation_id": validation_id,
                    "tool_name": tool_name,
                    "arguments": arguments_with_values
                },
            )
            question_validation = (
                "Do you permit the execution of this tool?\n"
                f"Tool: {tool_name}\nArguments:\n"
                "<arguments>\n"
                + "\n".join([f"    <{key}>{value}</{key}>" for key, value in arguments_with_values.items()])
                + "\n</arguments>\nYes or No"
            )
            permission_granted = await self.ask_for_user_validation(validation_id, question_validation)

            self._emit_event(
                "tool_execute_validation_end",
                {
                    "validation_id": validation_id,
                    "tool_name": tool_name,
                    "arguments": arguments_with_values,
                    "granted": permission_granted
                },
            )

            if not permission_granted:
                logger.debug(
                    "Tool '{}' validation denied, returning tool execution failure.",
                    tool_name,
                )
                return None, f"Error: execution of tool '{tool_name}' was denied by the user."

        self._emit_event("tool_execution_start", {"tool_name": tool_name, "arguments": arguments_with_values})

        try:
            arguments_with_values_interpolated = {
                key: await self._async_interpolate_variables(value) for key, value in arguments_with_values.items()
            }
            if tool.need_variables:
                arguments_with_values_interpolated["variables"] = self.variable_store
            if tool.need_caller_context_memory:
                arguments_with_values_interpolated["caller_context_memory"] = self.memory.memory

            converted_args = self.tools.validate_and_convert_arguments(tool_name, arguments_with_values_interpolated)
            injectable_properties = tool.get_injectable_properties_in_execution()
            for key, value in injectable_properties.items():
                converted_args[key] = value

            if hasattr(tool, "async_execute") and callable(tool.async_execute):
                result = tool.async_execute(**converted_args)
                if hasattr(result, "__await__"):
                    response = await result
                else:
                    response = result
            else:
                response = tool.execute(**converted_args)

            if tool.need_post_process:
                response = self._post_process_tool_response(tool_name, response)

            executed_tool = tool.name
        except Exception as e:
            response = f"Error executing tool: {tool_name}: {str(e)}\n"
            executed_tool = ""

        self._emit_event(
            "tool_execution_end", {"tool_name": tool_name, "arguments": arguments_with_values, "response": response}
        )
        return executed_tool, response

    async def _async_interpolate_variables(self, text: str, depth: int = 0) -> str:
        """Interpolate variables using $var$ syntax in the given text with recursion protection."""
        if not isinstance(text, str):
            return str(text)

        if depth > MAX_INTERPOLATION_DEPTH:
            logger.warning(f"Max interpolation depth ({MAX_INTERPOLATION_DEPTH}) reached, stopping recursion")
            return text

        try:
            import re

            for var in self.variable_store.keys():
                escaped_var = re.escape(var).replace('\\$', '$')
                pattern = f"\\${escaped_var}\\$"
                replacement = str(self.variable_store[var])
                text = re.sub(pattern, lambda m: replacement, text)

            if '$' in text and depth < MAX_INTERPOLATION_DEPTH:
                return await self._async_interpolate_variables(text, depth + 1)

            return text
        except Exception as e:
            logger.error(f"Error in _async_interpolate_variables: {str(e)}")
            return text

    def _interpolate_variables(self, text: str) -> str:
        """Interpolate variables using $var$ syntax in the given text (synchronous wrapper)."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self._async_interpolate_variables(text))

    def _compact_memory_if_needed(self, current_prompt: str = "") -> None:
        """Compacts the memory if it exceeds the maximum occupancy (synchronous wrapper)."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self._async_compact_memory_if_needed(current_prompt))

    async def _async_compact_memory_if_needed(self, current_prompt: str = "") -> None:
        """Compacts the memory if it exceeds the maximum occupancy or token limit."""
        ratio_occupied = self._calculate_context_occupancy()

        should_compact_by_occupancy = ratio_occupied >= MAX_OCCUPANCY
        should_compact_by_iteration = (
            self.compact_every_n_iterations is not None
            and self.current_iteration > 0
            and self.current_iteration % self.compact_every_n_iterations == 0
        )
        should_compact_by_token_limit = (
            self.max_tokens_working_memory is not None
            and self.total_tokens > self.max_tokens_working_memory
        )

        if should_compact_by_occupancy or should_compact_by_iteration or should_compact_by_token_limit:
            if should_compact_by_occupancy:
                logger.debug(f"Memory compaction triggered: Occupancy {ratio_occupied}% exceeds {MAX_OCCUPANCY}%")

            if should_compact_by_iteration:
                logger.debug(
                    f"Memory compaction triggered: Iteration {self.current_iteration} is a multiple of {self.compact_every_n_iterations}"
                )

            if should_compact_by_token_limit:
                logger.debug(
                    f"Memory compaction triggered: Token count {self.total_tokens} exceeds limit {self.max_tokens_working_memory}"
                )

            self._emit_event("memory_full")
            await self._async_compact_memory()
            self.total_tokens = self.model.token_counter_with_history(self.memory.memory, current_prompt)
            self._emit_event("memory_compacted")

    async def _async_compact_memory(self) -> None:
        """Compact memory asynchronously."""
        self.memory.compact()

    async def _async_compact_memory_with_summary(self) -> str:
        """Generate a summary and compact memory asynchronously."""
        memory_copy = self.memory.memory.copy()

        if len(memory_copy) < 3:
            logger.warning("Not enough messages to compact memory with summary")
            return "Memory compaction skipped: not enough messages"

        user_message = memory_copy.pop()
        assistant_message = memory_copy.pop()

        prompt_summary = self._render_template('memory_compaction_prompt.j2',
                                             conversation_history="\n\n".join(
                                                 f"[{msg.role.upper()}]: {msg.content}"
                                                 for msg in memory_copy
                                             ))

        summary = await self.model.async_generate(prompt=prompt_summary)

        if memory_copy and memory_copy[-1].role == "system":
            memory_copy.pop()

        memory_copy.append(Message(role="user", content=summary.response))
        memory_copy.append(assistant_message)
        memory_copy.append(user_message)
        self.memory.memory = memory_copy
        return summary.response

    def _generate_task_summary(self, content: str) -> str:
        """Generate a concise task-focused summary (synchronous wrapper)."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self._async_generate_task_summary(content))

    async def _async_generate_task_summary(self, content: str) -> str:
        """Generate a concise task-focused summary using the generative model."""
        try:
            if len(content) < 1024 * 4:
                return content

            prompt = self._render_template('task_summary_prompt.j2', content=content)
            result = await self.model.async_generate(prompt=prompt)
            logger.debug(f"Generated summary: {result.response}")
            return result.response.strip() + "\n🚨 The FULL task is in <task> tag in the previous messages.\n"
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            return f"Summary generation failed: {str(e)}"

    def _reset_session(self, task_to_solve: str = "", max_iterations: int = 30, clear_memory: bool = True) -> None:
        """Reset the agent's session."""
        logger.debug("Resetting session...")
        self.task_to_solve = task_to_solve
        if clear_memory:
            logger.debug("Clearing memory...")
            self.memory.reset()
            self.variable_store.reset()
            self.total_tokens = 0
        self.current_iteration = 0
        self.max_output_tokens = self.model.get_model_max_output_tokens() or DEFAULT_MAX_OUTPUT_TOKENS
        self.max_input_tokens = self.model.get_model_max_input_tokens() or DEFAULT_MAX_INPUT_TOKENS
        self.max_iterations = max_iterations

    def _update_total_tokens(self, message_history: list[Message], prompt: str) -> None:
        """Update the total tokens count based on message history and prompt."""
        self.total_tokens = self.model.token_counter_with_history(message_history, prompt)

    def _emit_event(self, event_type: str, data: dict[str, Any] | None = None) -> None:
        """Emit an event with system context and optional additional data."""
        event_data = {
            "iteration": self.current_iteration,
            "total_tokens": self.total_tokens,
            "context_occupancy": self._calculate_context_occupancy(),
            "max_input_tokens": self.max_input_tokens,
            "max_output_tokens": self.max_output_tokens,
        }
        if data:
            event_data.update(data)
        self.event_emitter.emit(event_type, event_data)

    def _parse_tool_usage(self, content: str) -> dict:
        """Extract tool usage from the response content."""
        if not content or not isinstance(content, str):
            return {}

        xml_parser = ToleranceXMLParser()
        action = xml_parser.extract_elements(text=content, element_names=["action"])

        tool_names = self.tools.tool_names()

        if action:
            tool_data = xml_parser.extract_elements(text=action["action"], element_names=tool_names)
            for tool_name in tool_data:
                if "<parameter_name>" in tool_data[tool_name]:
                    params = xml_parser.extract_elements(text=tool_data[tool_name], element_names=["parameter_name", "parameter_value"])
                    if "parameter_name" in params and "parameter_value" in params:
                        tool_data[tool_name] = {params["parameter_name"]: params["parameter_value"]}
            return tool_data
        else:
            return xml_parser.extract_elements(text=content, element_names=tool_names)

    def _parse_tool_arguments(self, tool: Tool, tool_input: str | dict) -> dict:
        """Parse the tool arguments from the tool input."""
        if isinstance(tool_input, dict):
            return tool_input
        tool_parser = ToolParser(tool=tool)
        return tool_parser.parse(tool_input)

    def _is_repeated_tool_call(self, tool_name: str, arguments_with_values: dict) -> bool:
        """Check if the tool call is repeated."""
        current_call = {
            "tool_name": tool_name,
            "arguments": arguments_with_values,
            "timestamp": datetime.now().isoformat(),
        }

        is_repeated_call = (
            self.last_tool_call.get("tool_name") == current_call["tool_name"]
            and self.last_tool_call.get("arguments") == current_call["arguments"]
        )

        if is_repeated_call:
            repeat_count = self.last_tool_call.get("count", 0) + 1
            current_call["count"] = repeat_count
        else:
            current_call["count"] = 1

        self.last_tool_call = current_call
        return is_repeated_call and current_call.get("count", 0) >= 2

    def _handle_no_tool_usage(self) -> ObserveResponseResult:
        """Handle the case where no tool usage is found in the response."""
        return ObserveResponseResult(
            next_prompt="Error: No tool usage found in response.", executed_tool=None, answer=None
        )

    def _normalize_final_answer(self, content: str) -> str:
        """Strip protocol markup from direct-answer responses so the UI gets visible text."""
        if not isinstance(content, str):
            return content

        text = content.strip()
        if not text:
            return text

        if not self._looks_like_protocol_markup(text):
            return text

        parser = ToleranceXMLParser()
        extracted = parser.extract_elements(text)

        for tag_name in (
            "answer",
            "execution_analysis",
            "decision_matrix",
            "memory_pad",
            "context_analysis",
            "thinking",
        ):
            value = extracted.get(tag_name, "").strip()
            normalized = self._collapse_visible_text(value)
            if normalized:
                return normalized

        stripped = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)
        stripped = re.sub(r"<[^>]+>", " ", stripped)
        stripped = self._collapse_visible_text(stripped)
        return stripped or text

    def _looks_like_protocol_markup(self, content: str) -> bool:
        """Detect XML-like protocol wrappers used by the runtime prompt."""
        lowered = content.lower()
        return any(f"<{tag}" in lowered or f"</{tag}" in lowered for tag in PROTOCOL_TAG_NAMES)

    def _collapse_visible_text(self, content: str) -> str:
        """Normalize whitespace after stripping protocol tags."""
        if not isinstance(content, str):
            return ""
        collapsed = re.sub(r"\s+", " ", content)
        return collapsed.strip()

    def _is_low_signal_response(self, content: str) -> bool:
        """Detect streaming outputs that contain only markdown/control shell and no user-visible content."""
        if not isinstance(content, str):
            return False

        stripped = content.strip()
        if not stripped:
            return True

        semantic = re.sub(r"[#>*`_\-\s~=\[\]\(\)\.:!|]+", "", stripped)
        return len(semantic) == 0

    # Chinese and English opening phrases that are likely incomplete when they appear
    # as the sole content — these are common LLM streaming prefixes.
    _TRUNCATED_PHRASE_PATTERNS = (
        # Chinese: short affirmative/opening phrases (exact matches only, no punctuation suffixes)
        ("我能",), ("可以",), ("当然",), ("好的",), ("好的，",),
        ("我来",), ("让我",), ("请稍等",), ("首先",),
        ("我可以",), ("我会",), ("我将",), ("没问题",),
        ("这个问",),
        # English: short opening phrases (exact matches only)
        ("Sure",), ("Okay",), ("I can",), ("Let me",),
        ("I'll",), ("Certainly",), ("Of course",),
    )

    def _is_incomplete_direct_reply(self, content: str) -> bool:
        """Detect streaming outputs that look like truncated opening phrases.

        Short affirmative/opening phrases like '我能' or 'Sure' appearing alone
        are almost certainly incomplete streaming artifacts, not finished answers.
        We trigger fallback to get the full response.

        A phrase is flagged as incomplete ONLY when the entire content equals
        the phrase (possibly followed only by whitespace). Content that merely
        STARTS WITH a phrase but continues with more text is NOT flagged.
        """
        if not isinstance(content, str):
            return False

        stripped = content.strip()
        # Must be short (under ~15 chars after strip) to be suspicious
        if len(stripped) > 15:
            return False

        if stripped in {"<", "</", "<a", "<t"}:
            return True

        # Empty / whitespace-only already caught by _is_low_signal_response
        if not stripped:
            return False

        # Common identity-prefix truncation in Chinese, e.g. "你是谁" -> "我是"
        if stripped == "我是":
            return True

        # Exact match with any truncated phrase
        for phrase, in self._TRUNCATED_PHRASE_PATTERNS:
            if stripped == phrase:
                return True

        return False

    def _handle_tool_not_found(self, tool_name: str) -> ObserveResponseResult:
        """Handle the case where the tool is not found."""
        logger.warning(f"Tool '{tool_name}' not found in tool manager.")
        return ObserveResponseResult(
            next_prompt=f"Error: Tool '{tool_name}' not found in tool manager.",
            executed_tool="",
            answer=None,
            tool_not_found=True,
        )

    def _handle_repeated_tool_call(self, tool_name: str, arguments_with_values: dict) -> tuple[str, str]:
        """Handle the case where a tool call is repeated."""
        repeat_count = self.last_tool_call.get("count", 0)
        error_message = self._render_template(
            'repeated_tool_call_error.j2',
            tool_name=tool_name,
            arguments_with_values=arguments_with_values,
            repeat_count=repeat_count
        )
        return tool_name, error_message

    def _handle_tool_execution_failure(self, response: str) -> ObserveResponseResult:
        """Handle the case where tool execution fails."""
        return ObserveResponseResult(
            next_prompt=response,
            executed_tool="",
            answer=None,
            tool_execution_failed=True,
        )

    def _handle_error(self, error: Exception) -> ObserveResponseResult:
        """Handle any exceptions that occur during response observation."""
        logger.error(f"Error in _observe_response: {str(error)}")
        return ObserveResponseResult(
            next_prompt=f"An error occurred while processing the response: {str(error)}",
            executed_tool=None,
            answer=None,
        )

    async def _async_observe_response_chat(self, content: str, iteration: int = 1) -> ObserveResponseResult:
        """Specialized observation method for chat mode with tool handling."""
        try:
            if "<action>" not in content:
                logger.debug(
                    "Runtime response classified as direct_reply (chat mode, no action): {}",
                    content[:500].replace("\n", "\\n"),
                )
                normalized = self._normalize_final_answer(content)
                return ObserveResponseResult(next_prompt=normalized, executed_tool=None, answer=normalized)

            parsed_content = self._parse_tool_usage(content)
            if not parsed_content:
                error_prompt = (
                    "⚠️ Error: Invalid tool call format detected. "
                    "Please use the exact XML structure:\n"
                    "```xml\n<action>\n<tool_name>\n  <parameter_name>value</parameter_name>\n</tool_name>\n</action>\n```"
                )
                return ObserveResponseResult(next_prompt=error_prompt, executed_tool=None, answer=None)

            if "task_complete" in parsed_content:
                feedback = (
                    "⚠️ Note: The 'task_complete' tool is not available in chat mode. "
                    "This is a conversational mode; tasks are not completed here. "
                    "Please use other tools or continue the conversation."
                )
                return ObserveResponseResult(next_prompt=feedback, executed_tool=None, answer=None)

            tool_names = list(parsed_content.keys())
            if self.tool_mode and self.tool_mode in self.tools.tool_names() and self.tool_mode in tool_names:
                tool_names = [self.tool_mode] + [t for t in tool_names if t != self.tool_mode]

            for tool_name in tool_names:
                if tool_name not in parsed_content:
                    continue

                tool_input = parsed_content[tool_name]
                tool = self.tools.get(tool_name)
                if not tool:
                    return self._handle_tool_not_found(tool_name)

                arguments_with_values = self._parse_tool_arguments(tool, tool_input)
                self._apply_default_parameters(tool, arguments_with_values)

                is_repeated_call = self._is_repeated_tool_call(tool_name, arguments_with_values)
                if is_repeated_call:
                    executed_tool, response = self._handle_repeated_tool_call(tool_name, arguments_with_values)
                else:
                    executed_tool, response = await self._async_execute_tool(tool_name, tool, arguments_with_values)

                if not executed_tool:
                    return self._handle_tool_execution_failure(response)

                variable_name = f"result_{executed_tool}_{iteration}"
                self.variable_store[variable_name] = response

                response_display = response
                if len(response) > MAX_RESPONSE_LENGTH:
                    response_display = response[:MAX_RESPONSE_LENGTH]
                    response_display += f"... (truncated, full content available in ${variable_name})"

                return ObserveResponseResult(
                    next_prompt=response_display,
                    executed_tool=executed_tool,
                    answer=None
                )

            return ObserveResponseResult(
                next_prompt="I tried to use a tool, but encountered an issue. Please try again with a different request.",
                executed_tool=None,
                answer=None
            )

        except Exception as e:
            return self._handle_error(e)

    def _apply_default_parameters(self, tool: Tool, arguments_with_values: dict) -> None:
        """Apply default parameters to tool arguments based on tool schema."""
        try:
            if tool.name == "duckduckgo_tool" and "max_results" not in arguments_with_values:
                logger.debug(f"Adding default max_results=5 for {tool.name}")
                arguments_with_values["max_results"] = "5"

            if hasattr(tool, "schema") and hasattr(tool.schema, "parameters"):
                for param_name, param_info in tool.schema.parameters.items():
                    if param_info.get("required", False) and param_name not in arguments_with_values:
                        if "default" in param_info:
                            logger.debug(f"Adding default value for {param_name} in {tool.name}")
                            arguments_with_values[param_name] = param_info["default"]
        except Exception as e:
            logger.debug(f"Error applying default parameters: {str(e)}")

    def _post_process_tool_response(self, tool_name: str, response: Any) -> str:
        """Process tool response for better presentation to the user."""
        if not isinstance(response, str):
            return response

        if response.strip().startswith(("{" , "[")) and response.strip().endswith(("}", "]")):
            try:
                import json
                parsed = json.loads(response)

                if isinstance(parsed, list) and parsed:
                    search_result_fields = ['title', 'href', 'url', 'body', 'content', 'snippet']
                    if isinstance(parsed[0], dict) and any(field in parsed[0] for field in search_result_fields):
                        formatted_results = []
                        for idx, result in enumerate(parsed, 1):
                            if not isinstance(result, dict):
                                continue

                            title = result.get('title', 'No title')
                            url = result.get('href', result.get('url', 'No link'))
                            description = result.get('body', result.get('content',
                                             result.get('snippet', result.get('description', 'No description'))))

                            formatted_results.append(f"{idx}. {title}\n   URL: {url}\n   {description}\n")

                        if formatted_results:
                            return "\n".join(formatted_results)

                return json.dumps(parsed, indent=2, ensure_ascii=False)

            except json.JSONDecodeError:
                pass

        return response

    def _format_observation_response(
        self, response: str, last_executed_tool: str, variable_name: str, iteration: int
    ) -> str:
        """Format the observation response with the given response, variable name, and iteration."""
        response_display = response
        if len(response) > MAX_RESPONSE_LENGTH:
            response_display = response[:MAX_RESPONSE_LENGTH]
            response_display += (
                f"... content was truncated full content available by interpolation in variable {variable_name}"
            )

        tools_prompt = self._get_tools_names_prompt()
        variables_prompt = self._get_variable_prompt()

        formatted_response = self._render_template(
            'observation_response_format.j2',
            iteration=iteration,
            max_iterations=self.max_iterations,
            task_to_solve_summary=self.task_to_solve_summary,
            tools_prompt=tools_prompt,
            variables_prompt=variables_prompt,
            last_executed_tool=last_executed_tool,
            variable_name=variable_name,
            response_display=response_display
        )

        return formatted_response

    def _prepare_prompt_task(self, task: str) -> str:
        """Prepare the initial prompt for the task."""
        tools_prompt = self._get_tools_names_prompt()
        variables_prompt = self._get_variable_prompt()

        prompt_task = self._render_template(
            'task_prompt.j2',
            task=task,
            tools_prompt=tools_prompt,
            variables_prompt=variables_prompt
        )
        return prompt_task

    def _get_tools_names_prompt(self) -> str:
        """Construct a detailed prompt that lists the available tools for task execution."""
        is_chat_mode = not self.task_to_solve.strip()

        if is_chat_mode:
            return self._get_tools_names_prompt_for_chat()

        tool_names = ', '.join(self.tools.tool_names())
        return self._render_template('tools_prompt.j2', tool_names=tool_names)

    def _get_tools_names_prompt_for_chat(self) -> str:
        """Construct a detailed prompt for chat mode that includes tool parameters, excluding task_complete."""
        tool_descriptions = []

        try:
            for tool_name in self.tools.tool_names():
                if tool_name == "task_complete":
                    continue

                try:
                    tool = self.tools.get(tool_name)
                    params = []

                    try:
                        if hasattr(tool, "schema") and hasattr(tool.schema, "parameters"):
                            schema_params = getattr(tool.schema, "parameters", {})
                            if isinstance(schema_params, dict):
                                for param_name, param_info in schema_params.items():
                                    if not isinstance(param_info, dict):
                                        continue

                                    required = "(required)" if param_info.get("required", False) else "(optional)"
                                    default = f" default: {param_info['default']}" if "default" in param_info else ""
                                    param_type = param_info.get("type", "string")
                                    param_desc = f"{param_name} ({param_type}) {required}{default}"
                                    params.append(param_desc)
                    except Exception as e:
                        logger.debug(f"Error parsing schema for {tool_name}: {str(e)}")

                    if tool_name == "googlenews":
                        params = [
                            "query (string, required) - The search query string",
                            "language (string, optional) default: en - Language code (e.g., en, fr, es)",
                            "period (string, optional) default: 7d - Time period (1d, 7d, 30d)",
                            "max_results (integer, required) default: 5 - Number of results to return",
                            "country (string, optional) default: US - Country code (e.g., US, GB, FR)",
                            "sort_by (string, optional) default: relevance - Sort by (relevance, date)",
                            "analyze (boolean, optional) default: False - Whether to analyze results"
                        ]
                    elif tool_name == "duckduckgosearch":
                        params = [
                            "query (string, required) - The search query string",
                            "max_results (integer, required) default: 5 - Number of results to return",
                            "time_period (string, optional) default: d - Time period (d: day, w: week, m: month)",
                            "region (string, optional) default: wt-wt - Region code for search results"
                        ]
                    elif tool_name == "llm":
                        params = [
                            "system_prompt (string, required) - The persona or system prompt to guide the language model's behavior",
                            "prompt (string, required) - The question to ask the language model. Supports interpolation with $var$ syntax",
                            "temperature (float, required) default: 0.5 - Sampling temperature between 0.0 and 1.0"
                        ]
                    elif tool_name == "task_complete":
                        params = [
                            "answer (string, required) - Your final answer or response to complete the task"
                        ]
                    elif "search" in tool_name.lower() and not params:
                        params.append("max_results (integer, optional) default: 5 - Number of results to return")

                    param_str = "\n  - ".join(params) if params else "No parameters required"
                    tool_descriptions.append(f"{tool_name}:\n  - {param_str}")
                except Exception as e:
                    logger.debug(f"Error processing tool {tool_name}: {str(e)}")
                    tool_descriptions.append(f"{tool_name}: Error retrieving parameters")
        except Exception as e:
            logger.debug(f"Error generating tool descriptions: {str(e)}")
            return "Error retrieving tool information"

        formatted_tools = "\n".join(tool_descriptions) if tool_descriptions else "No tools available."
        return formatted_tools

    def _get_variable_prompt(self) -> str:
        """Construct a prompt that explains how to use variables."""
        variable_names = ', '.join(self.variable_store.keys()) if len(self.variable_store.keys()) > 0 else "None"
        return self._render_template('variables_prompt.j2', variable_names=variable_names)

    def _calculate_context_occupancy(self) -> float:
        """Calculate the number of tokens in percentages for prompt and completion."""
        total_tokens = self.total_tokens
        max_tokens = self.model.get_model_max_input_tokens()

        if max_tokens is None or max_tokens <= 0:
            logger.warning(f"Invalid max tokens value: {max_tokens}. Using default of {DEFAULT_MAX_INPUT_TOKENS}.")
            max_tokens = DEFAULT_MAX_INPUT_TOKENS

        return round((total_tokens / max_tokens) * 100, 2)

    def _update_session_memory(self, user_content: str, assistant_content: str) -> None:
        """Log session messages to memory and emit events."""
        self.memory.add(Message(role="user", content=user_content))
        self._emit_event("session_add_message", {"role": "user", "content": user_content})

        self.memory.add(Message(role="assistant", content=assistant_content))
        self._emit_event("session_add_message", {"role": "assistant", "content": assistant_content})

    def update_model(self, new_model_name: str) -> None:
        """Update the model name and recreate the model wrapper instance."""
        self.model_name = new_model_name

    def add_tool(self, tool: Tool) -> None:
        """Add a new tool to the agent's tool manager."""
        if tool.name in self.tools.tool_names():
            raise ValueError(f"Tool with name '{tool.name}' already exists")

        self.tools.add(tool)
        self.config = AgentConfig(
            environment_details=self.config.environment_details,
            tools_markdown=self.tools.to_markdown(),
            system_prompt=self.config.system_prompt,
        )
        logger.debug(f"Added tool: {tool.name}")

    def remove_tool(self, tool_name: str) -> None:
        """Remove a tool from the agent's tool manager."""
        if tool_name not in self.tools.tool_names():
            raise ValueError(f"Tool '{tool_name}' does not exist")

        tool = self.tools.get(tool_name)
        if isinstance(tool, TaskCompleteTool):
            raise ValueError("Cannot remove TaskCompleteTool as it is required")

        self.tools.remove(tool_name)
        self.config = AgentConfig(
            environment_details=self.config.environment_details,
            tools_markdown=self.tools.to_markdown(),
            system_prompt=self.config.system_prompt,
        )
        logger.debug(f"Removed tool: {tool_name}")

    def set_tools(self, tools: list[Tool]) -> None:
        """Set/replace all tools for the agent."""
        if not any(isinstance(t, TaskCompleteTool) for t in tools):
            tools.append(TaskCompleteTool())

        tool_manager = ToolManager()
        tool_manager.add_list(tools)
        self.tools = tool_manager

        self.config = AgentConfig(
            environment_details=self.config.environment_details,
            tools_markdown=self.tools.to_markdown(),
            system_prompt=self.config.system_prompt,
        )
        logger.debug(f"Set {len(tools)} tools")

    def _render_template(self, template_name: str, **kwargs) -> str:
        """Render a Jinja2 template with the provided variables."""
        try:
            current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
            template_dir = current_dir / 'prompts'
            env = Environment(loader=FileSystemLoader(template_dir))
            template = env.get_template(template_name)
            return template.render(**kwargs)
        except Exception as e:
            logger.error(f"Error rendering template {template_name}: {str(e)}")
            raise

    def _track_file(self, file_path: str, tool_name: str) -> None:
        """Track files created or modified by tools."""
        try:
            if tool_name in ["write_file_tool", "writefile", "edit_whole_content", "replace_in_file", "replaceinfile", "EditWholeContent"]:
                if not file_path.startswith("/tmp/"):
                    file_path = os.path.join("/tmp", file_path.lstrip("/"))

            elif not os.path.isabs(file_path):
                file_path = os.path.abspath(os.path.join(os.getcwd(), file_path))

            tracked_path = os.path.realpath(file_path)

            if tool_name in ["write_file_tool", "writefile"] and not tracked_path.startswith("/tmp/"):
                logger.warning(f"Attempted to track file outside /tmp: {tracked_path}")
                return

            if tracked_path not in self.tracked_files:
                self.tracked_files.append(tracked_path)
                logger.debug(f"Added {tracked_path} to tracked files")

        except Exception as e:
            logger.error(f"Error tracking file {file_path}: {str(e)}")
