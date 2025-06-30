"""DAPEAgent package

High-level, multi-agent orchestration layer that sits on top of low-level
`azure_tools` helpers.  The main entry point will be the TriageAgent which
decides which task-specific agent to invoke.

For now the package just provides shared utilities – see `agent_builder` and
`utils.azure_adapters`.
""" 