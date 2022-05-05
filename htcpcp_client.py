import socket

# Options
# Eventually need to parse URI in TUI field to get
# IP and PORT from a field starting with "coffee://"
# as per RFC 2324 Section 2
IP = "127.0.0.1"
PORT = 8080


def construct_accept_additions():
    # TODO: construct based on checked options in TUI
    # Ref: RFC 2324 Sec. 2.2.2.1
    return "Accept-Additions: 0\r\n"

def construct_header():
    # Uses BREW method as per RFC 2324 Sec. 2.1.1
    # Could accept POST as well, but was deprecated as of 1998, so
    # the HTCPCP server will not accept POST
    # May later add support for GET, PROPFIND, and WHEN
    # in accordance with Sec. 2.1.2 - 2.1.4
    header = "HTTP/1.1 BREW\r\n"
    # Sec. 2.2.1.1 describes the SAFE header; not needed right now
    header += construct_accept_additions()
    header += "Content-Type: application/coffee-pot-command\r\n"
    header += "\r\n"
    return header

def construct_body():
    body = "coffee-message-body = stop \n"
    return body

#################
##### Main ######
#################

clientsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
clientsocket.connect((IP, PORT))

input("Press ENTER to send example HTCPCP message.")
header = construct_header()
body = construct_body()

clientsocket.send((construct_header() + construct_body()).encode("utf-8"))

received_message = clientsocket.recv(1024)
msg = received_message.decode()
print(msg)

clientsocket.close()

# GUI display eventually needs to contain an address field
# staring with "coffee://" according to RFC 2324 Section 2
