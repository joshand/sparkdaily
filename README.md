# sparkdaily
sparkdaily is designed to use the token of a bot user (not a bot account of a regular user). It will get a list of users for every
room that it is a part of, determine which messages those users have not viewed yet, and compile a daily digest (for yesterday) of
messages that each user did not see. This digest will then be e-mailed to those users (if there are no unread messages, no digest is
created).

This fork has been updated to use python3. It is also using the undocumented 'conversations' API of Spark to determine which messages
have been read or not.

Currently, this script is designed for only a single room. Although it will function with multiple rooms, it is not efficient for this
use. It will generate multiple messages, one per room per user, and the messages do not identify which room they are for. It should
be re-designed to generate a single message per user, with a per-room digest showing missed messages.
