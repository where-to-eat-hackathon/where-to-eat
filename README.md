# where-to-eat
## How to run
1. Build container images for `telegram_bot` and `nlp-service`. Use whatever `Dockerfile`-compatible tool you like
   (`docker`, `podman/buildah`, `kaniko`, etc)

   ```
   $ docker build -t nlp-service:latest -f nlp-service/Dockerfile ./nlp-service
   $ docker build -t telegram-bot:latest -f telegram_bot/Dockerfile ./telegram_bot
   ```

2. Update `.helm/values.yaml` with references to your images (don't forget to override `<component>.image.registry`
   if necessary), bot token secret.

3. Deploy to Kubernetes:
   ```
   $ cd .helm/
   $ helm dependency update
   $ helm upgrade --install --atomic --create-namespace -n where-to-eat - where-to-eat .
   ```
