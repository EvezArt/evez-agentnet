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
- VULTR (VULTR_API_KEY)
- Twitter/X (TWITTER_BEARER_TOKEN, when present in historical artifacts)
- Perplexity (PERPLEXITY_API_KEY, when present in historical artifacts)
- Gumroad (GUMROAD_ACCESS_TOKEN, when present in historical artifacts)

Do not paste replacement secrets into Git or store them in files such as `.env`. Inject them at runtime from the deployment secret manager.

Security invariant:

SECRET -> PROVIDER VAULT -> RUNTIME INJECTION

Never:

SECRET -> REPOSITORY -> AGENT MEMORY -> PUBLIC ARTIFACT