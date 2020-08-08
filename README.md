# slack-utils

## There are files packages in this repo
Message.py

Scanner.py

emoji.py

### emoji.py

emoji.py contains the class SlackEmoji.
From the SlackEmoji docstring:

    Basic class designed to handle all aspects of Slack's custom emoji.

    Slack does not have any public API methods for non Enterprise Grid teams
    other than emoji.list. This class exposes the hidden emoji.remove and 
    emoji.add API methods which allows authorized users to use their session 
    tokens (from the web browser) to add emojis.

    The following methods are provided (only required positional args are listed):
        add(image_source, emoji_name) --> Adds new emoji using an image url as a source
        alias(alias_name, emoji_name) --> Adds alias to existing emoji
        remove(emoji_name)            --> Deletes existing emoji by name
        test(image_source)            --> Tests Adding and Removing an emoji using an image url as a source

    A Slack Token with authorization to add emojis is required. Some Slack teams
    prevent users other than Team Owners and Admins from modifying emojis. In
    such teams, the token provided must be from an Admin or Team Owner account.

    Slack Tokens can be added either when initializing the class or after the
    class has been initialized.
        Option 1: emoji = SlackEmoji(TOKEN)
        Option 2: emoji = SlackEmoji()
                  emoji.setToken(TOKEN)

    Once the token is added, the team's domain name will be retrieved for use in
    the emoji.remove and emoji.add methods.
    
    Image resizing will be attempted to to make sure that excess borders will be 
    removed. Once uploaded, Slack will attempt to further resize the images. So far,
    this has proven effective at providing high quality emojis.
