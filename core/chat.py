
from core.prompts import SYSTEM_PROMPT
from tools.activity_logger import AgentActivityLogger


class JammerChat:
    def __init__(
        self,
        model,
        memory_manager,
        rag_pipeline=None,
        agent=None,
    ):
        self.model = model
        self.memory_manager = memory_manager
        self.rag_pipeline = rag_pipeline
        self.agent = agent
        self.history = []

        self.activity_logger = (
            agent.activity_logger
            if agent is not None
            and hasattr(agent, "activity_logger")
            else AgentActivityLogger()
        )

    # --------------------------------------------------
    # ACTIVITY LOGGING
    # --------------------------------------------------

    def _log_activity(self, event, **details):
        """Log activity without interrupting normal chat."""
        try:
            self.activity_logger.log(event, **details)
        except Exception as error:
            print(
                f"[Jammer] Activity logging failed: "
                f"{type(error).__name__}"
            )

    @staticmethod
    def _safe_input(user_input, limit=300):
        """Limit input length in logs to avoid oversized entries."""
        if not isinstance(user_input, str):
            return "<non-text input>"

        if len(user_input) > limit:
            return user_input[:limit] + "... [truncated]"

        return user_input

    # --------------------------------------------------
    # MESSAGE CONSTRUCTION
    # --------------------------------------------------

    def build_messages(self, user_input, include_rag=True):
        """Build model messages with system instructions, memory,
        optional document context, history, and the current input.
        """
        messages = []
        system_prompt = SYSTEM_PROMPT

        # Add persistent user memory.
        try:
            memory_context = self.memory_manager.format_memories(
                limit=20
            )

            if memory_context:
                system_prompt += (
                    "\n\nUSER MEMORY:\n"
                    + memory_context
                )

        except Exception as error:
            print(
                "[Jammer] Memory retrieval failed: "
                f"{type(error).__name__}"
            )
            self._log_activity(
                "memory_context_error",
                error=type(error).__name__,
            )

        # Add relevant document context when appropriate.
        if include_rag and self.rag_pipeline:
            try:
                rag_context = self.rag_pipeline.build_context(
                    user_input,
                    n_results=3,
                )

                if rag_context:
                    system_prompt += (
                        "\n\nDOCUMENT CONTEXT:\n"
                        + rag_context
                        + "\n\nUse the document context when it is "
                        "relevant to the user's question. Do not "
                        "invent facts that the context does not "
                        "support. If the documents do not contain "
                        "the answer, say so clearly. Provide a "
                        "direct final answer without revealing "
                        "internal reasoning."
                    )

            except Exception as error:
                print(
                    "[Jammer] Document retrieval failed: "
                    f"{type(error).__name__}"
                )
                self._log_activity(
                    "rag_context_error",
                    error=type(error).__name__,
                )

        messages.append(
            {
                "role": "system",
                "content": system_prompt,
            }
        )

        # Preserve existing conversation history.
        messages.extend(self.history)

        # Add the current user message.
        messages.append(
            {
                "role": "user",
                "content": user_input,
            }
        )

        return messages

    # --------------------------------------------------
    # TOOL SELECTION
    # --------------------------------------------------

    def select_tool(self, user_input):
        """Select an available local tool when appropriate."""
        if self.agent is None:
            return None

        try:
            return self.agent.selector.select(user_input)

        except Exception as error:
            print(
                "[Jammer] Tool selection failed: "
                f"{type(error).__name__}"
            )

            self._log_activity(
                "tool_selection_error",
                error=type(error).__name__,
            )

            return None

    # --------------------------------------------------
    # TOOL EXECUTION
    # --------------------------------------------------

    def execute_tool(self, selection):
        """Execute a selected tool and return its result."""
        if self.agent is None or selection is None:
            return None

        try:
            return self.agent.executor.execute(selection)

        except Exception as error:
            print(
                "[Jammer] Tool execution failed: "
                f"{type(error).__name__}"
            )

            tool_name = getattr(
                selection,
                "tool_name",
                None,
            )

            self._log_activity(
                "tool_execution_error",
                tool_name=tool_name,
                error=type(error).__name__,
            )

            return {
                "success": False,
                "used_tool": True,
                "tool_name": tool_name,
                "result": None,
                "error": type(error).__name__,
            }

    # --------------------------------------------------
    # UNSUPPORTED TERMINAL COMMAND HANDLING
    # --------------------------------------------------

    @staticmethod
    def _is_terminal_command_rejection(selection):
        """Identify the selector's explicit terminal-command guard.

        This intentionally matches the exact reason produced by
        the current selector. Other unsupported requests must
        remain eligible for normal conversational responses.
        """
        if selection is None:
            return False

        reason = getattr(selection, "reason", None)

        return (
            getattr(selection, "use_tool", True) is False
            and reason
            == "The input appears to be a terminal command."
        )

    def _add_terminal_command_notice(self, messages):
        """Tell the model that terminal commands are not executed."""
        messages.append(
            {
                "role": "system",
                "content": (
                    "TERMINAL COMMAND SAFETY NOTICE:\n"
                    "The user's input was identified as a terminal "
                    "or shell command. Jammer has not executed it. "
                    "Jammer does not have an enabled terminal "
                    "execution tool in this request. Do not claim "
                    "that the command was run, that files or system "
                    "settings were changed, or that any operation "
                    "succeeded. Briefly explain that you cannot "
                    "execute the command, and offer to explain it "
                    "or help the user run it manually if appropriate. "
                    "Do not attempt to execute it through another "
                    "tool."
                ),
            }
        )

        self._log_activity(
            "terminal_command_rejected",
            executed=False,
        )

    # --------------------------------------------------
    # TOOL RESULT CONTEXT
    # --------------------------------------------------

    
    def add_tool_result(self, messages, tool_result):
        """Pass actual tool success or failure to the model."""
        if not tool_result or not tool_result.get("used_tool"):
            return

        tool_name = tool_result.get("tool_name") or "unknown"

        if tool_result.get("success"):
            content = (
                f"Tool: {tool_name}\n"
                f"Tool Result: {tool_result.get('result')}\n\n"
                "A local Jammer tool executed successfully. "
                "Use its result accurately. Do not invent a "
                "different result or claim unconfirmed actions."
            )
        else:
            error = tool_result.get("error") or "Unknown tool error."

            content = (
                f"Tool error: {error}\n"
                f"Tool: {tool_name}\n\n"
                "The requested tool operation did not succeed. "
                "Explain the failure accurately. Do not pretend "
                "the operation succeeded or invent a result."
            )

        messages.append(
            {
                "role": "system",
                "content": content,
            }
        )


    # --------------------------------------------------
    # MAIN CHAT REQUEST
    # --------------------------------------------------

    def send(self, user_input):
        """Process one user message and return Jammer's response."""
        self._log_activity(
            "chat_request_started",
            input=self._safe_input(user_input),
        )

        # Step 1: Select a tool.
        selection = self.select_tool(user_input)

        terminal_rejected = (
            self._is_terminal_command_rejection(selection)
        )

        is_tool_request = (
            selection is not None
            and getattr(selection, "use_tool", False)
            and not terminal_rejected
        )

        self._log_activity(
            "chat_tool_decision",
            tool_selected=is_tool_request,
            tool_name=getattr(
                selection,
                "tool_name",
                None,
            ),
            reason=getattr(
                selection,
                "reason",
                None,
            ),
        )

        # Step 2: Execute only an explicitly selected tool.
        tool_result = (
            self.execute_tool(selection)
            if is_tool_request
            else None
        )

        # Step 3: Skip RAG for tool requests and rejected
        # terminal commands.
        include_rag = not (
            is_tool_request or terminal_rejected
        )

        rag_reason = (
            "terminal_command_rejected"
            if terminal_rejected
            else (
                "tool_request"
                if is_tool_request
                else "normal_chat"
            )
        )

        self._log_activity(
            "rag_decision",
            rag_enabled=include_rag,
            reason=rag_reason,
        )

        # Step 4: Build messages.
        messages = self.build_messages(
            user_input,
            include_rag=include_rag,
        )

        # Step 5: Add explicit safety context.
        if terminal_rejected:
            self._add_terminal_command_notice(messages)

        # Step 6: Add the actual result of any executed tool.
        self.add_tool_result(
            messages,
            tool_result,
        )

        # Step 7: Generate the response.
        try:
            response = self.model.generate(messages)

            if not isinstance(response, str):
                raise TypeError(
                    "The model returned a non-text response."
                )

            self._log_activity(
                "model_generation",
                success=True,
                response_length=len(response),
            )

        except Exception as error:
            self._log_activity(
                "model_generation",
                success=False,
                error=type(error).__name__,
            )

            self._log_activity(
                "chat_request_finished",
                success=False,
            )

            raise

        # Step 8: Save the conversation after successful generation.
        self.history.append(
            {
                "role": "user",
                "content": user_input,
            }
        )

        self.history.append(
            {
                "role": "assistant",
                "content": response,
            }
        )

        # Step 9: Retrieve source references for RAG answers.
        sources = []

        if include_rag and self.rag_pipeline:
            try:
                sources = self.rag_pipeline.get_sources(
                    user_input,
                    n_results=3,
                )

            except Exception as error:
                print(
                    "[Jammer] Source retrieval failed: "
                    f"{type(error).__name__}"
                )

                self._log_activity(
                    "rag_source_error",
                    error=type(error).__name__,
                )

        if sources:
            response += (
                "\n\nSources:\n"
                + "\n".join(
                    f"- {source}"
                    for source in sources
                )
            )

        # Step 10: Log completion.
        self._log_activity(
            "chat_request_finished",
            success=True,
            response_length=len(response),
            source_count=len(sources),
        )

        return response

    # --------------------------------------------------
    # CONVERSATION MANAGEMENT
    # --------------------------------------------------

    def clear(self):
        """Clear the current in-memory conversation history."""
        self.history.clear()

        self._log_activity(
            "conversation_cleared",
            success=True,
        )
