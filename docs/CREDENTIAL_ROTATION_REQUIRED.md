# Credential Rotation Required

The repository previously tracked a .env file containing credential assignments despite .gitignore excluding environment files.

The current file is being removed from the working tree. This is not equivalent to erasing the credentials from Git history.

Treat every credential that may have been present in that file as compromised until independently rotated or revoked at its provider.

Minimum rotation set includes credentials for:
- OpenClaw authentication
- GitHub
- OpenRouter
- OpenAI
- Groq
- Hugging Face
- Telegram

Do not paste replacement secrets into Git. Store them in the deployment secret manager or runtime environment.

Security invariant:

SECRET -> PROVIDER VAULT -> RUNTIME INJECTION

Never:

SECRET -> REPOSITORY -> AGENT MEMORY -> PUBLIC ARTIFACT