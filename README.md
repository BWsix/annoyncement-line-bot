# Annoyncement Line Bot

A Line bot for making announcements from one Line group to multiple Line groups.

### How to run the bot

#### Requirements

- python >= 3.8
- terraform >= 5
- aws account (each service used in this project is eligible for the AWS Free Tier)

#### Installation

1. Star this repo (thanks 😉)
2. **Fork** and clone **your repo** (could be a private one)
3. cd into `annoyncement-line-bot/terraform`
4. Copy `example.tfvars` to `prod.tfvars`
5. Configure `prod.tfvars`

   1. In `prod.tfvars`, change `repository` to your fork
   2. Generate a `Github personal access token (classic)`
      1. Go to <https://github.com/settings/tokens/new>
      2. Select `repo` and `admin:repo_hook`
      3. In `prod.tfvars`, change `github_access_token` to your token
   3. Create a line bot
      1. Go to <https://developers.line.biz/console/>
      2. Create a provider if you don't have one
      3. Create a new channel and select `Messaging API`
      4. In `Basic settings`, scroll to bottom and copy `Channel secret`
         1. In `prod.tfvars`, replace `linebot_secret` with your secret
      5. In `Messaging API`, scroll to bottom and issue a `Channel access token (long-lived)`
         1. In `prod.tfvars`, replace `linebot_token` with your token
      6. In `Messaging API`, scan the QRcode to add the bot as a friend
   4. Configure the line bot
      1. Go to <https://manager.line.biz/> and go the settings page by click on your bot
      2. Click `設定` on the top right corner of the page
      3. In `設定`>`帳號設定`>`功能切換`>`加入群組或多人聊天室`, choose `接受邀請加入群組或多人聊天室`
      4. In `設定`>`回應設定`>`回應設定`, enable `Webhook` and disable both `加入好友的歡迎訊息` and `自動回應訊息`

6. Apply the infrastructure

   1. Run `terraform init`
   2. Run `terraform apply -var-file prod.tfvars`
   3. Wait until `Apply complete!` shows up

7. Profit

   1. Invite the bot to the announcing group.\
      You will be prompted to set an `invite code`.
   2. Invite the bot to receiving groups.\
      The bot will send a link in the group, enter the invite code to activate the bot
   3. Make annoyncements
      1. In announcing group, type `annoy` or `Annoy`.
      2. Wait until the bot replies.
      3. Enter a text message or image message as your announcement
      4. It will show up on the receiving groups shortly
