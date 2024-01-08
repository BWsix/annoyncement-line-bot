# Annoyncement Line Bot - function

### Lambda functions

- `bot.lambda_update_webhook_url`\
  Called by terraform when running `terraform apply`
  - Updates line messaging api webhook url

- `bot.lambda_handle_linebot`\
  Called by line messaging api webhook when event happends
  - `JoinEvent`
    - If dynamo db is empty, save group id & name and prompt for invite code
    - Otherwise, sends a link to dashboard (url param contains group name & id)
  - `MessageEvent`
    - `TextMessage`:
      - If no invite code is set, treat message as invite code
      - If `message.lower()` == "annoy", save `waiting_for_input=true` and
        sender id in dynamodb
      - If `waiting_for_input` is `true` and message comes from command invoker,
        set `waiting_for_input=false` in dynamodb
        - `TextMessage`: push that message to receiving groups
        - `ImageMessage`:
          1. downloads image from line and save to s3
          2. generate a presigned url for public access
          3. generate image message from presigned url and push to receving
             groups

- `activation.lambda_handle_activation`\
  Called by user from dashboard
  - If invite code is correct, add group id and group name to dynamo db
