# HTCPCP-Modbus Application Gateway
# by Cameron Williams
# 3/25/2022
# This program is part of my master's project regarding the construction of an
# ICS testbed for brewing a cup of coffee. The role of this program is to
# reside on the Engineering Workstation Raspberry Pi in the Level 2
# (Supervisory) network zone of the testbed and receive HTCPCP requests from
# the Enterprise Workstation Raspberry Pi in the Level 3 (Enterprise) network
# via the Level 3 <-> Level 2 conduit. When valid HTCPCP requests are received,
# this program will convert the request to the equivalent Modbus command which
# will then be forwarded to the PLC in order to control the coffeepot.

import socket
from pymodbus.client.sync import ModbusTcpClient

# Options
HTCPCP_LISTEN_IP = "127.0.0.1"
HTCPCP_LISTEN_PORT = 8080

MODBUS_CLIENT_IP = "172.29.101.190"
MODBUS_UNIT_COFFEEPOT = 0x1
MODBUS_ADDRESS_COFFEEPOT_ON_OFF = 8225

# Other Global Vars
coffeepot_on_off = False

# Parsing the HTTP Method field; for now, simply returns True if the second
# "word" in the Method is "BREW"
def parse_header_method(method):
    method_parts = method.split(' ')
    if method_parts[1] == "BREW":
        return True
    else:
        return False

# Parse the Accept-Additions header field; for now, simply returns True if
# the field contains the value 0
def parse_header_accept_additions(accept_additions):
    if accept_additions[0] == "0":
        return True
    else:
        return False

# Parse the Content-Type header field; returns true only if it contains
# "application/coffeepot"
def parse_header_content_type(content_type):
    if content_type[0] == "application/coffee-pot-command":
        return True
    else:
        return False

# Parse the header into a dictionary with each header type becoming the key and
# their respective conent becoming the values for that key. For headers that don't
# have content, the key itself will be checked.
def parse_headers(header):
    # a dictionary seems most appropriate for this
    headers_dict = {}
    header_accepted = []

    try:
        header_lines = header.split("\r\n")
        for i in range(len(header_lines)):
            if ':' in header_lines[i]:
                header_parts = header_lines[i].split(": ")
                headers_dict[header_parts[0]] = []
                headers_dict[header_parts[0]].append(header_parts[1])
            else:
                headers_dict[header_lines[i]] = []
    except:
        print("Malformed request. Not replying.")
        return False

    #print(headers_dict)

    # first value in dict has to be the method
    # value is empty, just send key
    if parse_header_method(list(headers_dict.keys())[0]):
        print("Received BREW method. Proceeding.")
        header_accepted.append(True)
    else:
        print("Unsupported HTTP method.")
        header_accepted.append(False)

    if(parse_header_accept_additions(headers_dict["Accept-Additions"])):
        print("The listed additions are supported. Proceeding.")
        header_accepted.append(True)
    else:
        print("The listed additions are unsuppported.")
        header_accepted.append(False)

    if(parse_header_content_type(headers_dict["Content-Type"])):
        print("The Content-Type provided is acceptable. Proceeding.")
        header_accepted.append(True)
    else:
        print("The Content-Type provided is unsupported.")
        header_accepted.append(False)
    
    if False in header_accepted:
        return False
    else:
        return True

# Parse the coffee-message-body field from the message body; return True if it
# is well formed and set the global variable for whether the coffeepot should
# be turned on or off
def parse_body_coffee_message_body(coffee_message_body):

    global coffeepot_on_off

    if coffee_message_body[0] == 'start':
        print("Start found in coffepot-message-body")
        coffeepot_on_off = True
        return True
    elif coffee_message_body[0] == 'stop':
        coffeepot_on_off = False
        return True
    else:
        return False

# Parse the message body; return true if well formed. For each supported field
# in the message body, the value will be passed to a corresponding function
# will parse it and set some globabl variables that will be used during modbus
# interaction with the PLC controlling the coffee pot.
def parse_body(body):
    
    print("Message body is {}".format(body))
    
    body_dict = {}
    body_accepted = []

    try:
        body_lines = body.split(" \n")
        for i in range(len(body_lines)):
            if ' = ' in body_lines[i]:
                body_parts = body_lines[i].split(" = ")
                body_dict[body_parts[0]] = []
                body_dict[body_parts[0]].append(body_parts[1])
            else:
                body_dict[body_lines[i]] = []
        print("The body of the message is well formed. Proceed to interpreting components.")
    except:
        print("The body of the message is malformed.")
        return False
    
    if(parse_body_coffee_message_body(body_dict["coffee-message-body"])):
        print("Received well formed coffee-message-body. Proceeding.")
        body_accepted.append(True)
    else:
        print("Unsupported value in coffee-message-body field.")
        body_accepted.append(False)

    if False in body_accepted:
        return False
    else:
        return True

# Interacts with the coffeepot using the pymodbus library and returns the
# on/off status of the output connected to the coffeepot.
def coffeepot_interact():

    global coffeepot_on_off

    client = ModbusTcpClient(MODBUS_CLIENT_IP)

    if(coffeepot_on_off):
        result = client.write_coils(MODBUS_ADDRESS_COFFEEPOT_ON_OFF, [True]*1, unit=MODBUS_UNIT_COFFEEPOT)
        if result.isError():
            print("Failed to send ON signal. Connection problem?")
            return False
        else:
            result = client.read_coils(MODBUS_ADDRESS_COFFEEPOT_ON_OFF, 8, unit=MODBUS_UNIT_COFFEEPOT)
            if result.isError():
                print("Failed to check Modbus coil status. Connection problem?")
            return True, result.bits[0]
    else:
        result = client.write_coils(MODBUS_ADDRESS_COFFEEPOT_ON_OFF, [False]*1, unit=MODBUS_UNIT_COFFEEPOT)
        if result.isError():
            print("Failed to send OFF signal. Connection problem?")
            return False
        else:
            result = client.read_coils(MODBUS_ADDRESS_COFFEEPOT_ON_OFF, 8, unit=MODBUS_UNIT_COFFEEPOT)
            if result.isError():
                print("Failed to check Modbus coil status. Connection problem?")
            return True, result.bits[0]

def bad_request():
    connection.send("HTTP/1.1 400 Bad Reqeust".encode("utf-8"))

###############################################################################
##### Main ####################################################################
###############################################################################

serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
serversocket.bind((HTCPCP_LISTEN_IP, HTCPCP_LISTEN_PORT))
serversocket.listen(100)

while True:
    connection, address = serversocket.accept()
    received_message = connection.recv(1024)

    msg = received_message.decode()
    msg_split = msg.split("\r\n\r\n")
    rcv_header = msg_split[0]
    rcv_body = msg_split[1]
    print("The header received through the socket was {}".format(rcv_header))
    print("The body received through the socket was {}".format(rcv_body))


    if(parse_headers(rcv_header)):
        print("Headers were of acceptable form and contained acceptable values. Proceed to processing message body.")
        if(parse_body(rcv_body)):
            interact_success, coffeepot_status = coffeepot_interact()
            print("Interaction success: {}, Coffeepot Status: {}".format(interact_success, coffeepot_status))
        else:
            bad_request()
    else:
        bad_request()
    
    #msg = bytes((header + html).format(length, timestamp), "utf-8") # changed
    #clientsocket.send(msg)
    #clientsocket.close()