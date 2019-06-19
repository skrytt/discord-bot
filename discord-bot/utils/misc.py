''' Utility methods which don't belong elsewhere.
'''
import logging
import sys
import traceback

def get_required_bot_permissions_value():
    ''' Get a permissions value as an integer that can be inserted in a Discord URL to
        invite a bot to a guild.
    '''
    permissions = (
        (1 << 10)   # 0x00000400 READ_MESSAGES
        + (1 << 11) # 0x00000800 SEND_MESSAGES
        + (1 << 14) # 0x00004000 EMBED_LINKS
        + (1 << 18) # 0x00020000 MENTION_EVERYONE
        + (1 << 19) # 0x00040000 USE_EXTERNAL_EMOJIS
        + (1 << 28) # 0x10000000 MANAGE_ROLES
    )
    return permissions

def get_invite_link(client_id):
    perm_value = get_required_bot_permissions_value()
    return 'https://discordapp.com/oauth2/authorize?&client_id=%s&scope=bot&permissions=%s' % (
            client_id, perm_value)

def log_traceback(logger):
    trace = traceback.extract_tb(sys.exc_info()[2])
    logger.error('Traceback: ')
    # Lines are four part tuples (file, linenum, funcname, text)
    for line in trace:
        logger.error('%s %d %s ', line[0], line[1], line[2])
        logger.error('    %s', line[3])
