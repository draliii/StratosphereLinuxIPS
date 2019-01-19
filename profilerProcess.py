import multiprocessing
import json
from datetime import datetime
from datetime import timedelta
import sys
from collections import OrderedDict
import configparser
from slips.core.database import __database__
import time
import ipaddress

def timing(f):
    """ Function to measure the time another function takes."""
    def wrap(*args):
        time1 = time.time()
        ret = f(*args)
        time2 = time.time()
        print('Function took {:.3f} ms'.format((time2-time1)*1000.0))
        return ret
    return wrap

# Profiler Process
class ProfilerProcess(multiprocessing.Process):
    """ A class to create the profiles for IPs and the rest of data """
    def __init__(self, inputqueue, outputqueue, config, width):
        multiprocessing.Process.__init__(self)
        self.inputqueue = inputqueue
        self.outputqueue = outputqueue
        self.config = config
        self.width = width
        self.columns_defined = False
        self.timeformat = ''
        # Read the configuration
        self.read_configuration()
        # Set the database
        __database__.setOutputQueue(self.outputqueue)

    def read_configuration(self):
        """ Read the configuration file for what we need """
        # Get the home net if we have one from the config
        try:
            self.home_net = ipaddress.ip_network(self.config.get('parameters', 'home_network'))
        except (configparser.NoOptionError, configparser.NoSectionError, NameError):
            # There is a conf, but there is no option, or no section or no configuration file specified
            self.home_net = False

        # Get the time window width, if it was not specified as a parameter 
        if not self.width:
            try:
                data = self.config.get('parameters', 'time_window_width')
                self.width = float(data)
            except ValueError:
                # Its not a float
                if 'only_one_tw' in data:
                    # Only one tw. Width is 10 9s, wich is ~11,500 days, ~311 years
                    self.width = 9999999999
            except configparser.NoOptionError:
                # By default we use 300 seconds, 5minutes
                self.width = 300.0
            except (configparser.NoOptionError, configparser.NoSectionError, NameError):
                # There is a conf, but there is no option, or no section or no configuration file specified
                self.width = 300.0
        # Limit any width to be > 0. By default we use 300 seconds, 5minutes
        elif self.width < 0:
            self.width = 300.0
        else:
            self.width = 300.0
        # Report the time window width
        if self.width == 9999999999:
            self.outputqueue.put("10|profiler|Time Windows Width used: Only 1 time windows. Dates in the names of files are 100 years in the past.".format(self.width))
        else:
            self.outputqueue.put("10|profiler|Time Windows Width used: {} seconds.".format(self.width))

        # Get the format of the time in the flows
        try:
            self.timeformat = config.get('timestamp', 'format')
        except (configparser.NoOptionError, configparser.NoSectionError, NameError):
            # There is a conf, but there is no option, or no section or no configuration file specified
            self.timeformat = '%Y/%m/%d %H:%M:%S.%f'

        ##
        # Get the direction of analysis
        try:
            self.analysis_direction = self.config.get('parameters', 'analysis_direction')
        except (configparser.NoOptionError, configparser.NoSectionError, NameError):
            # There is a conf, but there is no option, or no section or no configuration file specified
            # By default 
            self.analysis_direction = 'all'

    def process_columns(self, line):
        """
        Analyze the line and detect the format
        Valid formats are:
            - CSV, typically generated by the ra tool of Argus
                - In the case of CSV, recognize commas or TABS as field separators
            - JSON, typically generated by Suricata
        The function returns True when the colums are alredy defined, which means you can continue analyzing the data. A return of False means the columns were not defined, but we defined now.
        A return of -2 means an error
        """
        self.column_values = {}
        self.column_values['starttime'] = False
        self.column_values['endtime'] = False
        self.column_values['dur'] = False
        self.column_values['proto'] = False
        self.column_values['appproto'] = False
        self.column_values['saddr'] = False
        self.column_values['sport'] = False
        self.column_values['dir'] = False
        self.column_values['daddr'] = False
        self.column_values['dport'] = False
        self.column_values['state'] = False
        self.column_values['pkts'] = False
        self.column_values['spkts'] = False
        self.column_values['dpkts'] = False
        self.column_values['bytes'] = False
        self.column_values['sbytes'] = False
        self.column_values['dbytes'] = False

        # If the columns are already defined, just get the correct values fast using indexes. If not, find the columns
        if self.columns_defined:
            # Read the lines fast
            nline = line.strip().split(self.separator)
            try:
                self.column_values['starttime'] = datetime.strptime(nline[self.column_idx['starttime']], self.timeformat)
            except IndexError:
                pass
            try:
                self.column_values['endtime'] = nline[self.column_idx['endtime']]
            except IndexError:
                pass
            try:
                self.column_values['dur'] = nline[self.column_idx['dur']]
            except IndexError:
                pass
            try:
                self.column_values['proto'] = nline[self.column_idx['proto']]
            except IndexError:
                pass
            try:
                self.column_values['appproto'] = nline[self.column_idx['appproto']]
            except IndexError:
                pass
            try:
                self.column_values['saddr'] = nline[self.column_idx['saddr']]
            except IndexError:
                pass
            try:
                self.column_values['sport'] = nline[self.column_idx['sport']]
            except IndexError:
                pass
            try:
                self.column_values['dir'] = nline[self.column_idx['dir']]
            except IndexError:
                pass
            try:
                self.column_values['daddr'] = nline[self.column_idx['daddr']]
            except IndexError:
                pass
            try:
                self.column_values['dport'] = nline[self.column_idx['dport']]
            except IndexError:
                pass
            try:
                self.column_values['state'] = nline[self.column_idx['state']]
            except IndexError:
                pass
            try:
                self.column_values['pkts'] = nline[self.column_idx['pkts']]
            except IndexError:
                pass
            try:
                self.column_values['spkts'] = nline[self.column_idx['spkts']]
            except IndexError:
                pass
            try:
                self.column_values['dpkts'] = nline[self.column_idx['dpkts']]
            except IndexError:
                pass
            try:
                self.column_values['bytes'] = nline[self.column_idx['bytes']]
            except IndexError:
                pass
            try:
                self.column_values['sbytes'] = nline[self.column_idx['sbytes']]
            except IndexError:
                pass
            try:
                self.column_values['dbytes'] = nline[self.column_idx['dbytes']]
            except IndexError:
                pass
        else:
            # Find the type of lines, and the columns indexes
            # These are the indexes for later
            self.column_idx = {}
            self.column_idx['starttime'] = False
            self.column_idx['endtime'] = False
            self.column_idx['dur'] = False
            self.column_idx['proto'] = False
            self.column_idx['appproto'] = False
            self.column_idx['saddr'] = False
            self.column_idx['sport'] = False
            self.column_idx['dir'] = False
            self.column_idx['daddr'] = False
            self.column_idx['dport'] = False
            self.column_idx['state'] = False
            self.column_idx['pkts'] = False
            self.column_idx['spkts'] = False
            self.column_idx['dpkts'] = False
            self.column_idx['bytes'] = False
            self.column_idx['sbytes'] = False
            self.column_idx['dbytes'] = False

            try:
                # Heuristic detection: can we read it as json?
                try:
                    data = json.loads(line)
                    data_type = 'json'
                except ValueError:
                    data_type = 'csv'

                if data_type == 'json':
                    # Only get the suricata flows, not all!
                    if data['event_type'] != 'flow':
                        return -2
                    # JSON
                    self.column_values['starttime'] = datetime.strptime(data['flow']['start'].split('+')[0], '%Y-%m-%dT%H:%M:%S.%f') # We do not process timezones now
                    self.column_values['endtime'] = datetime.strptime(data['flow']['end'].split('+')[0], '%Y-%m-%dT%H:%M:%S.%f')  # We do not process timezones now
                    difference = self.column_values['endtime'] - self.column_values['starttime']
                    self.column_values['dur'] = difference.total_seconds()
                    self.column_values['proto'] = data['proto']
                    try:
                        self.column_values['appproto'] = data['app_proto']
                    except KeyError:
                        pass
                    self.column_values['saddr'] = data['src_ip']
                    try:
                        self.column_values['sport'] = data['src_port']
                    except KeyError:
                        # Some protocols like icmp dont have ports
                        self.column_values['sport'] = '0'
                    # leave dir as default
                    self.column_values['daddr'] = data['dest_ip']
                    try:
                        self.column_values['dport'] = data['dest_port']
                    except KeyError:
                        # Some protocols like icmp dont have ports
                        column_values['dport'] = '0'
                    self.column_values['state'] = data['flow']['state']
                    self.column_values['pkts'] = int(data['flow']['pkts_toserver']) + int(data['flow']['pkts_toclient'])
                    self.column_values['spkts'] = int(data['flow']['pkts_toserver'])
                    self.column_values['dpkts'] = int(data['flow']['pkts_toclient'])
                    self.column_values['bytes'] = int(data['flow']['bytes_toserver']) + int(data['flow']['bytes_toclient'])
                    self.column_values['sbytes'] = int(data['flow']['bytes_toserver'])
                    self.column_values['dbytes'] = int(data['flow']['bytes_toclient'])
                elif data_type == 'csv':
                    # Are we using commas or tabs?. Just count them and choose as separator the char with more counts
                    nr_commas = len(line.split(','))
                    nr_tabs = len(line.split('	'))
                    if nr_commas > nr_tabs:
                        # Commas is the separator
                        self.separator = ','
                    elif nr_tabs > nr_commas:
                        # Tabs is the separator
                        self.separator = '	'
                    else:
                        self.outputqueue.put("01|profiler|[Profiler] Error. The file is not comma or tab separated.")
                        return -2
                    nline = line.strip().split(self.separator)
                    for field in nline:
                        if 'time' in field.lower():
                            self.column_idx['starttime'] = nline.index(field)
                        elif 'dur' in field.lower():
                            self.column_idx['dur'] = nline.index(field)
                        elif 'proto' in field.lower():
                            self.column_idx['proto'] = nline.index(field)
                        elif 'srca' in field.lower():
                            self.column_idx['saddr'] = nline.index(field)
                        elif 'sport' in field.lower():
                            self.column_idx['sport'] = nline.index(field)
                        elif 'dir' in field.lower():
                            self.column_idx['dir'] = nline.index(field)
                        elif 'dsta' in field.lower():
                            self.column_idx['daddr'] = nline.index(field)
                        elif 'dport' in field.lower():
                            self.column_idx['dport'] = nline.index(field)
                        elif 'state' in field.lower():
                            self.column_idx['state'] = nline.index(field)
                        elif 'totpkts' in field.lower():
                            self.column_idx['pkts'] = nline.index(field)
                        elif 'totbytes' in field.lower():
                            self.column_idx['bytes'] = nline.index(field)
                self.columns_defined = True
            except Exception as inst:
                self.outputqueue.put("01|profiler|\tProblem in process_columns() in profilerProcess.")
                self.outputqueue.put("01|profiler|"+str(type(inst)))
                self.outputqueue.put("01|profiler|"+str(inst))
                sys.exit(1)
            # This is the return when the columns were not defined. False
            return False
        # This is the return when the columns were defined. True
        return True

    def add_flow_to_profile(self, columns):
        """ 
        This is the main function that takes a flow and does all the magic to convert it into a working data in our system. 
        It includes checking if the profile exists and how to put the flow correctly.
        """
        # Get data
        try:
            saddr = columns['saddr']
            sport = columns['sport']
            daddr = columns['daddr']
            dport = columns['dport']
            proto = columns['proto']
            separator = __database__.getFieldSeparator()
            profileid = 'profile' + separator + str(saddr)
            starttime = time.mktime(columns['starttime'].timetuple())
            # Create the objects of IPs
            try:
                saddr_as_obj = ipaddress.IPv4Address(saddr) 
                daddr_as_obj = ipaddress.IPv4Address(daddr) 
                # Is ipv4
            except ipaddress.AddressValueError:
                # Is it ipv6?
                try:
                    saddr_as_obj = ipaddress.IPv6Address(saddr) 
                    daddr_as_obj = ipaddress.IPv6Address(daddr) 
                except ipaddress.AddressValueError:
                    # Its a mac
                    return False

            # Check if the ip received is part of our home network. We only crate profiles for our home network
            if self.home_net and saddr_as_obj in self.home_net:
                # Its in our Home network

                # The steps for adding a flow in a profile should be
                # 1. Add the profile to the DB. If it already exists, nothing happens. So now profileid is the id of the profile to work with. 
                # The width is unique for all the timewindow in this profile. 
                # Also we only need to pass the width for registration in the DB. Nothing operational
                __database__.addProfile(profileid, starttime, self.width)

                # 3. For this profile, find the id in the databse of the tw where the flow belongs.
                twid = self.get_timewindow(starttime, profileid)

            elif self.home_net and saddr_as_obj not in self.home_net:
                # The src ip is not in our home net

                # Check that the dst IP is in our home net
                if daddr_as_obj in self.home_net:
                    self.outputqueue.put("07|profiler|[Profiler] Flow with dstip in homenet: srcip {}, dstip {}".format(saddr_as_obj, daddr_as_obj))
                    # The dst ip is in the home net. So register this as going to it
                    # 1. Get the profile of the dst ip.
                    profileid = __database__.getProfileIdFromIP(daddr_as_obj)
                    if not profileid:
                        # We do not have yet the profile of the dst ip that is in our home net
                        self.outputqueue.put("07|profiler|[Profiler] The dstip profile was not here... create")
                        temp_profileid = 'profile' + separator + str(daddr_as_obj)
                        #self.outputqueue.put("01|profiler|Created profileid for dstip: {}".format(temp_profileid))
                        __database__.addProfile(temp_profileid, starttime, self.width)
                        # Try again
                        profileid = __database__.getProfileIdFromIP(daddr_as_obj)
                        if not profileid:
                            # Too many errors. We should not be here
                            return False
                    self.outputqueue.put("07|profiler|[Profile] Profile for dstip {} : {}".format(daddr_as_obj, profileid))
                    # 2. For this profile, find the id in the databse of the tw where the flow belongs.
                    twid = self.get_timewindow(starttime, profileid)
                elif daddr_as_obj not in self.home_net:
                    # The dst ip is also not part of our home net. So ignore completely
                    return False
            elif not self.home_net:
                # We don't have a home net, so create profiles for everyone

                # The steps for adding a flow in a profile should be
                # 1. Add the profile to the DB. If it already exists, nothing happens. So now profileid is the id of the profile to work with. 
                # The width is unique for all the timewindow in this profile
                __database__.addProfile(profileid, starttime, self.width)

                # 3. For this profile, find the id in the databse of the tw where the flow belongs.
                twid = self.get_timewindow(starttime, profileid)

            ##########################################
            # Now that we have the profileid and twid, add the data from the flow in this tw for this profile
            self.outputqueue.put("07|profiler|[Profiler] Storing data in the profile: {}".format(profileid))
            # In which analysis mode are we?
            if self.analysis_direction == 'out':
                if saddr_as_obj in self.home_net:
                    # Add the tuple
                    __database__.add_out_tuple(profileid, twid, daddr_as_obj, dport, proto)
                    # Add the dstip
                    __database__.add_out_dstips(profileid, twid, daddr_as_obj)
                    # Add the dstport
                    __database__.add_out_dstport(profileid, twid, dport)
                    # Add the srcport
                    __database__.add_out_srcport(profileid, twid, sport)
            elif self.analysis_direction == 'all':
                # Was the flow coming FROM the profile ip?
                if saddr_as_obj in self.home_net:
                    # Add the tuple
                    __database__.add_out_tuple(profileid, twid, daddr_as_obj, dport, proto)
                    # Add the dstip
                    __database__.add_out_dstips(profileid, twid, daddr_as_obj)
                    # Add the dstport
                    __database__.add_out_dstport(profileid, twid, dport)
                    # Add the srcport
                    __database__.add_out_srcport(profileid, twid, sport)
                # Was the flow coming TO the profile ip?
                elif daddr_as_obj in self.home_net:
                    # The dstip was in the homenet
                    # Add the srcip
                    __database__.add_in_srcips(profileid, twid, saddr_as_obj)
                    # Add the dstport
                    __database__.add_in_dstport(profileid, twid, dport)
                    # Add the srcport
                    __database__.add_in_srcport(profileid, twid, sport)
        except Exception as inst:
            # For some reason we can not use the output queue here.. check
            self.outputqueue.put("01|profiler|Error in add_flow_to_profile profilerProcess.")
            self.outputqueue.put("01|profiler|{}".format((type(inst))))
            self.outputqueue.put("01|profiler|{}".format(inst))

    def get_timewindow(self, flowtime, profileid):
        """" 
        This function should get the id of the TW in the database where the flow belong.
        If the TW is not there, we create as many tw as necessary in the future or past until we get the correct TW for this flow.
        - We use this function to avoid retrieving all the data from the DB for the complete profile. We use a separate table for the TW per profile.
        -- Returns the time window id
        THIS IS NOT WORKING:
        - The empty profiles in the middle are not being created!!!
        - The Dtp ips are stored in the first time win
        """
        try:
            # First check of we are not in the last TW. Since this will be the majority of cases
            try:
                [(lasttwid, lasttw_start_time)] = __database__.getLastTWforProfile(profileid)
                lasttwid = lasttwid.decode("utf-8")
                lasttw_start_time = float(lasttw_start_time)
                lasttw_end_time = lasttw_start_time + self.width
                flowtime = float(flowtime)
                self.outputqueue.put("04|profiler|[Profiler] The last TW id was {}. Start:{}. End: {}".format(lasttwid, lasttw_start_time, lasttw_end_time ))
                # There was a last TW, so check if the current flow belongs here.
                if lasttw_end_time > flowtime and lasttw_start_time <= flowtime:
                    self.outputqueue.put("04|profiler|[Profiler] The flow ({}) is on the last time window ({})".format(flowtime, lasttw_end_time))
                    twid = lasttwid
                elif lasttw_end_time <= flowtime:
                    # The flow was not in the last TW, its NEWER than it
                    self.outputqueue.put("04|profiler|[Profiler] The flow ({}) is NOT on the last time window ({}). Its newer".format(flowtime, lasttw_end_time))
                    amount_of_new_tw = int((flowtime - lasttw_end_time) / self.width)
                    self.outputqueue.put("04|profiler|[Profiler] We have to create {} empty TWs in the midle.".format(amount_of_new_tw))
                    temp_end = lasttw_end_time
                    for id in range(0, amount_of_new_tw + 1):
                        new_start = temp_end 
                        twid = __database__.addNewTW(profileid, new_start)
                        self.outputqueue.put("04|profiler|[Profiler] Creating the TW id {}. Start: {}.".format(twid, new_start))
                        temp_end = new_start + self.width
                    # Now get the id of the last TW so we can return it
                elif lasttw_start_time > flowtime:
                    # The flow was not in the last TW, its OLDER that it
                    self.outputqueue.put("04|profiler|[Profiler] The flow ({}) is NOT on the last time window ({}). Its older".format(flowtime, lasttw_end_time))
                    # Find out if we already have this TW in the past
                    data = __database__.getTWforScore(profileid, flowtime)
                    if data:
                        # We found a TW where this flow belongs to
                        (twid, tw_start_time) = data
                        twid = twid.decode("utf-8")
                        return twid
                    else:
                        # There was no TW that included the time of this flow, so create them in the past
                        # How many new TW we need in the past?
                        amount_of_new_tw = int((lasttw_end_time - flowtime) / self.width)
                        amount_of_current_tw = __database__.getamountTWsfromProfile(profileid)
                        diff = amount_of_new_tw - amount_of_current_tw
                        self.outputqueue.put("05|profiler|[Profiler] We need to create {} TW before the first".format(diff))
                        # Get the first TW
                        [(firsttwid, firsttw_start_time)] = __database__.getFirstTWforProfile(profileid)
                        firsttwid = firsttwid.decode("utf-8")
                        firsttw_start_time = float(firsttw_start_time)
                        # The start of the new older TW should be the first - the width
                        temp_start = firsttw_start_time - self.width
                        for id in range(0, diff + 1):
                            new_start = temp_start
                            # The method to add an older TW is the same as to add a new one, just the starttime changes
                            twid = __database__.addNewOlderTW(profileid, new_start)
                            self.outputqueue.put("02|profiler|[Profiler] Creating the new older TW id {}. Start: {}.".format(twid, new_start))
                            temp_start = new_start - self.width
            except ValueError:
                # There is no last tw. So create the first TW
                # If the option for only-one-tw was selected, we should create the TW at least 100 years before the flowtime, to cover for
                # 'flows in the past'. Which means we should cover for any flow that is coming later with time before the first flow
                if self.width == 9999999999:
                    # Seconds in 1 year = 31536000
                    startoftw = float(flowtime - (31536000 * 100))
                else:
                    startoftw = float(flowtime)
                # Add this TW, of this profile, to the DB
                twid = __database__.addNewTW(profileid, startoftw)
                #self.outputqueue.put("01|profiler|First TW ({}) created for profile {}.".format(twid, profileid))
            return twid
        except Exception as e:
            print('Error in get_timewindow()')
            print(e)


    def run(self):
        # Main loop function
        try:
            rec_lines = 0
            while True:
                # If the input communication queue is empty, just wait
                if self.inputqueue.empty():
                    pass
                else:
                    # The input communication queue is not empty, we are receiving
                    line = self.inputqueue.get()
                    if 'stop' == line:
                        self.outputqueue.put("01|profiler|Stopping Profiler Process.")
                        self.outputqueue.put("10|profiler|Total Received Lines: {}".format(rec_lines))
                        return True
                    else:
                        # Received new input data
                        # Extract the columns smartly
                        self.outputqueue.put("03|profiler| < Received Line: {}".format(line.replace('\n','')))
                        if self.process_columns(line):
                            # Add the flow to the profile
                            self.add_flow_to_profile(self.column_values)
                            rec_lines += 1
        except KeyboardInterrupt:
            print('Received {} lines'.format(rec_lines))
            return True
        except Exception as inst:
            print('Received {} lines'.format(rec_lines))
            self.outputqueue.put("01|profiler|\tProblem with Profiler Process.")
            self.outputqueue.put("01|profiler|"+str(type(inst)))
            self.outputqueue.put("01|profiler|"+str(inst.args))
            self.outputqueue.put("01|profiler|"+str(inst))
            sys.exit(1)
