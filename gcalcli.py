#!/usr/local/bin/python

# NOTE(ryanb): i'm maintaining my own copy of this because the author hasn't
# updated it since 10/2007. this file is based on the 1.4.0 release from
# http://code.google.com/p/gcalcli/ with:
#
# - /usr/local/bin/python
# - the sys.stdout = ... and sys.stderr = ... lines commented out as
#   described in http://code.google.com/p/gcalcli/issues/detail?id=10 . that
#   prevents a UnicodeEncodeError on events with non-ascii characters in them.

# $Id: gcalcli 61 2007-10-13 18:44:46Z insanum $

# ** The MIT License **
#
# Copyright (c) 2007 Eric Davis (aka Insanum)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


#
# Home: http://code.google.com/p/gcalcli
#
# Author: Eric Davis <insanum@gmail.com> <http://www.insanum.com>
#
# Requirements:
#  - Python - http://www.python.org
#  - Google's GData Python module - http://code.google.com/p/gdata-python-client
#  - ElementTree Python module - http://effbot.org/zone/element-index.htm
#  - dateutil Python module - http://www.labix.org/python-dateutil
#
# TODO (maybe):
#  - import meeting.ics Outlook events ("gcalcli import <file|stdin>")
#  - add (non-quick) events with ability to set reminders, repeat, guests, etc
#  - configurable 'remind' reminders (i.e. 30 mins before event every 5 mins)
#  - daemon mode for 'remind' reminders (working from cached data)
#  - cache calendar information (serialize calendar info to file)
#  - man page anyone?
#

__username__ = '<username>@gmail.com'
__password__ = '<password>'

__program__ = 'gcalcli'
__version__ = 'v1.4'
__author__  = 'Insanum'

import inspect

import sys, os, re, urllib, getopt, shlex, codecs, locale
from ConfigParser import ConfigParser
from gdata.calendar.service import *
from datetime import *
from dateutil.tz import *
from dateutil.parser import *


# for unicode support
# sys.stdout = codecs.getwriter(locale.getpreferredencoding())(sys.stdout)
# sys.stdin = codecs.getreader(locale.getpreferredencoding())(sys.stdin)


def Usage():
    sys.stdout.write('''
Usage:

gcalcli [options] command [command args]

 Options:

  --help                   this usage text

  --config <file>          config file to read (default is '~/.gcalclirc')

  --user <username>        google username

  --pw <password>          password

  --cals [all,             'calendars' to work with (default is all calendars)
          default,         - default (your default main calendar)
          owner,           - owner (your owned calendars)
          editor,          - editor (editable calendar)
          contributor,     - contributor (non-owner but able to edit)
          read,            - read (read only calendars)
          freebusy]        - freebusy (only free/busy info visible)

  --cal <name>             'calendar' to work with (default is all calendars)
                           - you can specify a calendar by name or by using a
                             regular expression to match multiple calendars
                           - you can use multiple '--cal' arguments on the
                             command line

  --details                show all event details (i.e. length, location,
                           reminders, contents)

  --ignore-started         ignore old or already started events
                           - when used with the 'agenda' command, ignore events
                             that have already started and are in-progress with
                             respect to the specified [start] time
                           - when used with the 'search' command, ignore events
                             that have already occurred and only show future
                             events

  --width                  the number of characters to use for each column in
                           the 'cal' command output (default is 10)

  --nc                     don't use colors

  --cal-owner-color        specify the colors used for the calendars and dates
  --cal-editor-color       each of these argument requires a <color> argument
  --cal-contributor-color  which must be one of [ default, black, brightblack,
  --cal-read-color         red, brightred, green, brightgreen, yellow,
  --cal-freebusy-color     brightyellow, blue, brightblue, magenta,
  --date-color             brightmagenta, cyan, brightcyan, white,
  --border-color           brightwhite ]

 Commands:

  list                     list all calendars

  search <text>            search for events
                           - only matches whole words

  agenda [start] [end]     get an agenda for a time period
                           - start time default is 12am today
                           - end time default is 5 days from start
                           - example time strings:
                              '9/24/2007'
                              'Sep 24 2007 3:30pm'
                              '2007-09-24T15:30'
                              '2007-09-24T15:30-8:00'
                              '20070924T15'
                              '8am'

  calw <weeks> [start]     get a week based agenda in a nice calendar format
                           - weeks is the number of weeks to display
                           - start time default is beginning of this week
                           - note that all events for the week(s) are displayed

  calm [start]             get a month agenda in a nice calendar format
                           - start time default is the beginning of this month
                           - note that all events for the month are displayed
                             and only one month will be displayed

  quick <text>             quick add an event to your default calendar
                           - example:
                              'Dinner with Eric 7pm tomorrow'
                              '5pm 10/31 Trick or Treat'

  remind <mins> <command>  execute command if event occurs within <mins>
                           minutes time ('%s' in <command> is replaced with
                           event start time and title text)
                           - <mins> default is 10
                           - default command:
                              'gxmessage -display :0 -center \\
                                         -title "Ding, Ding, Ding!" %s'
''')
    sys.exit(1)


class CLR:

    useColor = True

    def __str__(self):
        if self.useColor: return self.color
        else: return ""

class CLR_NRM(CLR):   color = "[0m"
class CLR_BLK(CLR):   color = "[0;30m"
class CLR_BRBLK(CLR): color = "[30;1m"
class CLR_RED(CLR):   color = "[0;31m"
class CLR_BRRED(CLR): color = "[31;1m"
class CLR_GRN(CLR):   color = "[0;32m"
class CLR_BRGRN(CLR): color = "[32;1m"
class CLR_YLW(CLR):   color = "[0;33m"
class CLR_BRYLW(CLR): color = "[33;1m"
class CLR_BLU(CLR):   color = "[0;34m"
class CLR_BRBLU(CLR): color = "[34;1m"
class CLR_MAG(CLR):   color = "[0;35m"
class CLR_BRMAG(CLR): color = "[35;1m"
class CLR_CYN(CLR):   color = "[0;36m"
class CLR_BRCYN(CLR): color = "[36;1m"
class CLR_WHT(CLR):   color = "[0;37m"
class CLR_BRWHT(CLR): color = "[37;1m"


def PrintErrMsg(msg):
    if CLR.useColor:
        sys.stdout.write(str(CLR_BRRED()))
        sys.stdout.write(msg)
        sys.stdout.write(str(CLR_NRM()))
    else:
        sys.stdout.write(msg)


def PrintMsg(color, msg):
    if CLR.useColor:
        sys.stdout.write(str(color))
        sys.stdout.write(msg)
        sys.stdout.write(str(CLR_NRM()))
    else:
        sys.stdout.write(msg)


def DebugPrint(msg):
    return
    sys.stdout.write(str(CLR_YLW()))
    sys.stdout.write(msg)
    sys.stdout.write(str(CLR_NRM()))


class GoogleCalendar:

    gcal          = None
    allCals       = None
    workCals      = []
    now           = datetime.now(tzlocal())
    feedPrefix    = 'http://www.google.com/calendar/feeds/'
    agendaLength  = 5
    username      = ''
    password      = ''
    access        = ''
    workCalNames  = []
    details       = False
    ignoreStarted = False
    calWidth      = 10
    calMonday     = False
    command       = 'gxmessage -display :0 -center -title "Ding, Ding, Ding!" %s'

    calOwnerColor       = CLR_CYN()
    calEditorColor      = CLR_NRM()
    calContributorColor = CLR_NRM()
    calReadColor        = CLR_MAG()
    calFreeBusyColor    = CLR_NRM()
    dateColor           = CLR_YLW()
    borderColor         = CLR_WHT()

    ACCESS_ALL         = 'all'      # non-google access level
    ACCESS_DEFAULT     = 'default'  # non-google access level
    ACCESS_NONE        = 'none'
    ACCESS_OWNER       = 'owner'
    ACCESS_EDITOR      = 'editor'
    ACCESS_CONTRIBUTOR = 'contributor'
    ACCESS_READ        = 'read'
    ACCESS_FREEBUSY    = 'freebusy'


    def __init__(self,
                 username='',
                 password='',
                 access='all',
                 workCalNames=[],
                 details=False,
                 ignoreStarted=False,
                 calWidth=10,
                 calMonday=False,
                 calOwnerColor=CLR_CYN(),
                 calEditorColor=CLR_GRN(),
                 calContributorColor=CLR_NRM(),
                 calReadColor=CLR_MAG(),
                 calFreeBusyColor=CLR_NRM(),
                 dateColor=CLR_GRN(),
                 borderColor=CLR_WHT()):

        self.gcal          = CalendarService()
        self.username      = username
        self.password      = password
        self.access        = access
        self.workCalNames  = workCalNames
        self.details       = details
        self.ignoreStarted = ignoreStarted
        self.calWidth      = calWidth
        self.calMonday     = calMonday

        self.calOwnerColor       = calOwnerColor
        self.calEditorColor      = calEditorColor
        self.calContributorColor = calContributorColor
        self.calReadColor        = calReadColor
        self.calFreeBusyColor    = calFreeBusyColor
        self.dateColor           = dateColor
        self.borderColor         = borderColor

        # authenticate and login to google calendar
        try:
            self.gcal.ClientLogin(
                            username=self.username,
                            password=self.password,
                            service='cl',
                            source=__author__+'-'+__program__+'-'+__version__)
        except:
            PrintErrMsg("Error: Failed to authenticate with Google Calendar!\n")
            sys.exit(1)

        # get the list of calendars
        self.allCals = self.gcal.GetAllCalendarsFeed()

        order = { self.ACCESS_OWNER       : 1,
                  self.ACCESS_EDITOR      : 2,
                  self.ACCESS_CONTRIBUTOR : 3,
                  self.ACCESS_READ        : 4,
                  self.ACCESS_FREEBUSY    : 5,
                  self.ACCESS_NONE        : 6 }

        self.allCals.entry.sort(lambda x, y:
                                cmp(order[x.access_level.value],
                                    order[y.access_level.value]))

        for cal in self.allCals.entry:

            cal.gcalcli_altLink = cal.GetAlternateLink().href
            match = re.match('^' + self.feedPrefix + '(.*?)/(.*?)/(.*)$',
                             cal.gcalcli_altLink)
            cal.gcalcli_username    = urllib.unquote(match.group(1))
            cal.gcalcli_visibility  = urllib.unquote(match.group(2))
            cal.gcalcli_projection  = urllib.unquote(match.group(3))

            if len(self.workCalNames):
                for wc in self.workCalNames:
                    if re.search(wc.lower(), cal.title.text.lower()):
                        self.workCals.append(cal)
            else:
                self.workCals.append(cal)



    def _CalendarWithinAccess(self, cal):

        if (self.access == self.ACCESS_ALL):

            return True

        elif ((self.access == self.ACCESS_DEFAULT) and
              (cal.gcalcli_username == self.username)):

            return True

        elif (self.access != cal.access_level.value):

            return False

        return True


    def _CalendarColor(self, cal):

        if (cal == None):
            return CLR_NRM()
        elif (cal.access_level.value == self.ACCESS_OWNER):
            return self.calOwnerColor
        elif (cal.access_level.value == self.ACCESS_EDITOR):
            return self.calEditorColor
        elif (cal.access_level.value == self.ACCESS_CONTRIBUTOR):
            return self.calContributorColor
        elif (cal.access_level.value == self.ACCESS_FREEBUSY):
            return self.calFreeBusyColor
        elif (cal.access_level.value == self.ACCESS_READ):
            return self.calReadColor
        else:
            return CLR_NRM()


    def _GetWeekEventStrings(self, cmd, curMonth,
                             startDateTime, endDateTime, eventList):

        weekEventStrings = [ '', '', '', '', '', '', '' ]

        for event in eventList:

            eventStartDateTime = \
                parse(event.when[0].start_time,
                      default=startDateTime).astimezone(tzlocal())

            if ((cmd == 'calm') and
                (curMonth != eventStartDateTime.strftime("%b"))):
                continue

            dayNum = int(eventStartDateTime.strftime("%w"))

            if ((eventStartDateTime >= startDateTime) and
                (eventStartDateTime <= endDateTime)):

                meridiem = eventStartDateTime.strftime('%p').lower()
                tmpTimeStr = eventStartDateTime.strftime("%l:%M") + meridiem
                # newline and empty string are the keys to turn off coloring
                weekEventStrings[dayNum] += \
                    "\n" + \
                    str(self._CalendarColor(event.gcalcli_cal)) + \
                    tmpTimeStr.strip() + " " + event.title.text.strip()

        return weekEventStrings


    def _GetCutIndex(self, eventString, idx):

        cut1 = eventString.find('\n')
        cut2 = eventString.find(' ')

        DebugPrint("-- %s\n" % (eventString))

        if ((idx + len(eventString)) <= self.calWidth):
            DebugPrint("--- %d (end of string)\n" % (idx + len(eventString)))
            return (idx + len(eventString))

        if (cut1 < 0):
            if ((cut2 < 0) or (cut2 >= self.calWidth)):
                cut = self.calWidth
            else:
                cut = cut2
        elif (cut2 < 0):
            if ((cut1 < 0) or (cut1 >= self.calWidth)):
                cut = self.calWidth
            else:
                cut = cut1
        else:
            if ((cut1 <= cut2) and (cut1 < self.calWidth)):
                cut = cut1
            elif ((cut2 <= cut1) and (cut2 < self.calWidth)):
                cut = cut2
            else:
                cut = self.calWidth

        DebugPrint("== %d (initial cut)\n" % (cut))
        if ((cut == 0) or ((idx + cut) > self.calWidth)):
            DebugPrint("** %d (no more) %s\n" % (idx, eventString))
            return idx

        if ((idx + cut) < self.calWidth):
            while ((cut < len(eventString)) and (eventString[cut] == ' ')):
                DebugPrint("! skipping space\n")
                cut += 1
            DebugPrint("=== %d (new cut)\n" % (cut))
            DebugPrint("!! recurse (%d)\n" % (idx + cut))
            cut = self._GetCutIndex(eventString[cut:], (idx + cut))
            DebugPrint("!!!! %d %s\n" % (cut, eventString))
            return cut

        DebugPrint("** %d cut %s\n" % (idx, eventString))
        return (idx + cut)


    def _GraphEvents(self, cmd, startDateTime, count, eventList):

        # ignore started events (i.e. that start previous day and end start day)
        while (len(eventList) and
               ((parse(eventList[0].when[0].start_time,
                      default=startDateTime).astimezone(tzlocal())) <
                startDateTime)):
            eventList = eventList[1:]

        dayDivider = ''
        for i in xrange(self.calWidth):
            dayDivider += '-'

        weekDivider = ''
        for i in xrange(7):
            weekDivider += '+'
            weekDivider += dayDivider
        weekDivider += '+'
        weekDivider = str(self.borderColor) + weekDivider + str(CLR_NRM())

        empty = ''
        for i in xrange(self.calWidth):
            empty += ' '

        dayFormat = '%-' + str(self.calWidth) + '.' + str(self.calWidth) + 's'

        # XXX this table needs to change to use current locale (strftime %A)
        dayNames = [ 'Sunday', 'Monday', 'Tuesday', 'Wednesday',
                     'Thursday', 'Friday', 'Saturday' ]

        dayHeader = str(self.borderColor) + '|' + str(CLR_NRM())
        for i in xrange(7):
            if self.calMonday:
                if i == 6:
                    dayName = dayFormat % (dayNames[0])
                else:
                    dayName = dayFormat % (dayNames[i+1])
            else:
                dayName = dayFormat % (dayNames[i])
            dayHeader += str(self.dateColor) + dayName + str(CLR_NRM())
            dayHeader += str(self.borderColor) + '|' + str(CLR_NRM())

        PrintMsg(CLR_NRM(), "\n" + weekDivider + "\n")
        if (cmd == 'calm'):
            m = startDateTime.strftime('%B %Y')
            mw = str((self.calWidth * 7) + 6)
            mwf = '%-' + mw + '.' + mw + 's'
            PrintMsg(CLR_NRM(),
                     str(self.borderColor) + '|' + str(CLR_NRM()) + \
                     str(self.dateColor) + mwf % (m) + str(CLR_NRM()) + \
                     str(self.borderColor) + '|' + str(CLR_NRM()) + '\n')
            PrintMsg(CLR_NRM(), weekDivider + "\n")
        PrintMsg(CLR_NRM(), dayHeader + "\n")
        PrintMsg(CLR_NRM(), weekDivider + "\n")

        curMonth = startDateTime.strftime("%b")

        # get date range objects for the first week
        if (cmd == 'calm'):
            dayNum = startDateTime.strftime("%w")
            startDateTime = (startDateTime - timedelta(days=int(dayNum)))
        startWeekDateTime = startDateTime
        endWeekDateTime = (startWeekDateTime + timedelta(days=7))

        for i in xrange(count):

            # create/print date line
            line = str(self.borderColor) + '|' + str(CLR_NRM())
            for j in xrange(7):
                if (cmd == 'calw'):
                    d = (startWeekDateTime +
                         timedelta(days=j)).strftime("%e %b")
                else: # (cmd == 'calm'):
                    d = (startWeekDateTime +
                         timedelta(days=j)).strftime("%e")
                    if (curMonth != (startWeekDateTime +
                                     timedelta(days=j)).strftime("%b")):
                        d = ''
                todayMarker = ''
                if (self.now.strftime("%e%b%Y") ==
                    (startWeekDateTime + timedelta(days=j)).strftime("%e%b%Y")):
                    todayMarker = " ***"
                line += str(self.dateColor) + \
                            dayFormat % (d + todayMarker) + \
                        str(CLR_NRM()) + \
                        str(self.borderColor) + \
                            '|' + \
                        str(CLR_NRM())
            PrintMsg(CLR_NRM(), line + "\n")

            weekColorStrings = [ '', '', '', '', '', '', '' ]
            weekEventStrings = self._GetWeekEventStrings(cmd, curMonth,
                                                         startWeekDateTime,
                                                         endWeekDateTime,
                                                         eventList)

            # get date range objects for the next week
            startWeekDateTime = endWeekDateTime
            endWeekDateTime = (endWeekDateTime + timedelta(days=7))

            while 1:

                done = True
                line = str(self.borderColor) + '|' + str(CLR_NRM())

                for j in xrange(7):

                    if (weekEventStrings[j] == ''):
                        weekColorStrings[j] = ''
                        line += empty + \
                                str(self.borderColor) + '|' + str(CLR_NRM())
                        continue

                    if (weekEventStrings[j][0] == ''):
                        # get/skip over color sequence
                        weekColorStrings[j] = ''
                        while (weekEventStrings[j][0] != 'm'):
                            weekColorStrings[j] += weekEventStrings[j][0]
                            weekEventStrings[j] = weekEventStrings[j][1:]
                        weekColorStrings[j] += weekEventStrings[j][0]
                        weekEventStrings[j] = weekEventStrings[j][1:]

                    if (weekEventStrings[j][0] == '\n'):
                        weekColorStrings[j] = ''
                        weekEventStrings[j] = weekEventStrings[j][1:]
                        line += empty + \
                                str(self.borderColor) + '|' + str(CLR_NRM())
                        done = False
                        continue

                    weekEventStrings[j] = weekEventStrings[j].lstrip()

                    cut = self._GetCutIndex(weekEventStrings[j], 0)

                    line += weekColorStrings[j] + \
                            dayFormat % (weekEventStrings[j][:cut]) + \
                            str(CLR_NRM())
                    weekEventStrings[j] = weekEventStrings[j][cut:]

                    done = False
                    line += str(self.borderColor) + '|' + str(CLR_NRM())

                if done:
                    break

                PrintMsg(CLR_NRM(), line + "\n")

            PrintMsg(CLR_NRM(), weekDivider + "\n")


    def _PrintEvents(self, defaultDateTime, startDateTime, eventList):

        if (len(eventList) == 0):
            PrintMsg(CLR_YLW(), "\nNo Events Found...\n")
            return

        timeFormat = '%l:%M'
        dayFormat = '\n%a %b %d' # 10 chars for day
        indent = '          ' # 10 spaces
        detailsIndent = '                   '    # 19 spaces
        day = ''

        for event in eventList:
            eventStartDateTime = \
                parse(event.when[0].start_time,
                      default=defaultDateTime).astimezone(tzlocal())

            if (self.ignoreStarted and (eventStartDateTime < startDateTime)):
                continue

            tmpDayStr  = eventStartDateTime.strftime(dayFormat)
            meridiem = eventStartDateTime.strftime('%p').lower()
            tmpTimeStr = eventStartDateTime.strftime(timeFormat) + meridiem
            prefix = indent
            if (tmpDayStr != day): day = prefix = tmpDayStr
            PrintMsg(self.dateColor, prefix)
            PrintMsg(self._CalendarColor(event.gcalcli_cal),
                     '  %-7s  %s\n' % (tmpTimeStr, event.title.text))

            if self.details:

                clr = CLR_NRM()

                if event.where[0].value_string:
                    str = "%s  Location: %s\n" % (detailsIndent,
                                                 event.where[0].value_string)
                    PrintMsg(clr, str)

                if event.when[0].end_time:
                    eventEndDateTime = parse(event.when[0].end_time,
                                  default=defaultDateTime).astimezone(tzlocal())
                    diffDateTime = (eventEndDateTime - eventStartDateTime)
                    str = "%s  Length: %s\n" % (detailsIndent, diffDateTime)
                    PrintMsg(clr, str)

                # XXX Why does accessing event.when[0].reminder[0] fail?
                for rem in event.when[0].reminder:
                    remStr = ''
                    if rem.days:
                        remStr += "%s Days" % (rem.days)
                    if rem.hours:
                        if (remStr != ''):
                            remStr += ' '
                        remStr += "%s Hours" % (rem.hours)
                    if rem.minutes:
                        if (remStr != ''):
                            remStr += ' '
                        remStr += "%s Minutes" % (rem.minutes)
                    str = "%s  Reminder: %s\n" % (detailsIndent, remStr)
                    PrintMsg(clr, str)

                if event.content.text:
                    str = "%s  Content: %s\n" % (detailsIndent,
                                                event.content.text)
                    PrintMsg(clr, str)


    def _GetAllEvents(self, cal, feed):

        eventList = []

        while 1:
            next = feed.GetNextLink()

            for event in feed.entry:
                event.gcalcli_cal = cal
                eventList.append(event)

            if not next:
                break

            feed = self.gcal.GetCalendarEventFeed(next.href)

        return eventList


    def _SearchForCalEvents(self, start, end, defaultDateTime, searchText):

        eventList = []

        for cal in self.workCals:

            if not self._CalendarWithinAccess(cal):
                continue

            # see http://code.google.com/apis/calendar/reference.html#Parameters
            if not searchText:
                query = CalendarEventQuery(cal.gcalcli_username,
                                           cal.gcalcli_visibility,
                                           cal.gcalcli_projection)
                query.start_min = start.isoformat()
                query.start_max = end.isoformat()
            else:
                query = CalendarEventQuery(cal.gcalcli_username,
                                           cal.gcalcli_visibility,
                                           cal.gcalcli_projection,
                                           searchText)
            query.singleevents = 'true'
            # we sort later after getting events from all calendars
            #query.orderby = 'starttime'
            #query.sortorder = 'ascending'
            feed = self.gcal.CalendarQuery(query)

            eventList.extend(self._GetAllEvents(cal, feed))

        eventList.sort(lambda x, y:
                       cmp(parse(x.when[0].start_time,
                                 default=defaultDateTime).astimezone(tzlocal()),
                           parse(y.when[0].start_time,
                                 default=defaultDateTime).astimezone(tzlocal())))

        return eventList


    def ListAllCalendars(self):

        accessLen = 0

        for cal in self.allCals.entry:
            length = len(cal.access_level.value)
            if (length > accessLen): accessLen = length

        if (accessLen < len('Access')): accessLen = len('Access')

        format = ' %0' + str(accessLen) + 's  %s\n'

        PrintMsg(CLR_BRYLW(), "\n" + format % ('Access', 'Title'))
        PrintMsg(CLR_BRYLW(), format % ('------', '-----'))

        for cal in self.allCals.entry:
            PrintMsg(self._CalendarColor(cal),
                     format % (cal.access_level.value, cal.title.text))


    def TextQuery(self, searchText=''):

        # the empty string would get *ALL* events...
        if (searchText == ''):
            return

        eventList = self._SearchForCalEvents(None, None, self.now, searchText)

        self._PrintEvents(self.now, self.now, eventList)


    def AgendaQuery(self, startText='', endText=''):

        # convert now to midnight this morning and use for default
        today = self.now.replace(hour=0, minute=0, second=0, microsecond=0)

        if (startText == ''):
            start = today
        else:
            try:
                start = parse(startText, default=today)
            except:
                PrintErrMsg('\nError: failed to parse start time\n')
                return

        if (endText == ''):
            end = (start + timedelta(days=self.agendaLength))
        else:
            try:
                end = parse(endText, default=today)
            except:
                PrintErrMsg('\nError: failed to parse end time\n')
                return

        eventList = self._SearchForCalEvents(start, end, start, None)

        self._PrintEvents(today, start, eventList)


    def CalQuery(self, cmd, startText='', count=1):

        # convert now to midnight this morning and use for default
        today = self.now.replace(hour=0, minute=0, second=0, microsecond=0)

        if (startText == ''):
            start = today
        else:
            try:
                start = parse(startText, default=today)
                start = start.replace(hour=0, minute=0, second=0, microsecond=0)
            except:
                PrintErrMsg('\nError: failed to parse start time\n')
                return

        # convert start date to the beginning of the week or month
        if (cmd == 'calw'):
            dayNum = start.strftime("%w")
            start = (start - timedelta(days=int(dayNum)))
            end = (start + timedelta(days=(count * 7)))
        else: # (cmd == 'calwm'):
            start = (start - timedelta(days=(start.day - 1)))
            endMonth = (start.month + 1)
            endYear = start.year
            if (endMonth == 13):
                endMonth = 1
                endYear += 1
            end = start.replace(month=endMonth, year=endYear)
            daysInMonth = (end - start).days
            offsetDays = int(start.strftime('%w'))
            totalDays = (daysInMonth + offsetDays)
            count = (totalDays / 7)
            if (totalDays % 7):
                count += 1

        eventList = self._SearchForCalEvents(start, end, start, None)

        self._GraphEvents(cmd, start, count, eventList)


    def QuickAdd(self, eventText):

        if (eventText == ''):
            return

        quickEvent = gdata.calendar.CalendarEventEntry()
        quickEvent.content = atom.Content(text=eventText)
        quickEvent.quick_add = gdata.calendar.QuickAdd(value='true')

        self.gcal.InsertEvent(quickEvent,
                              '/calendar/feeds/default/private/full')


    def Remind(self, minutes=10, command=None):

        if (command == None):
            command = self.command

        # perform a date query for now + minutes + slip
        start = self.now
        end   = (start + timedelta(minutes=(minutes + 5)))

        eventList = self._SearchForCalEvents(start, end, start, None)

        message = ''

        for event in eventList:
            today = self.now.replace(hour=0, minute=0, second=0, microsecond=0)
            eventStartDateTime = parse(event.when[0].start_time,
                                       default=today).astimezone(tzlocal())

            # skip this event if it already started
            # XXX maybe add a 2+ minute grace period here...
            if (eventStartDateTime < self.now):
                continue

            meridiem = eventStartDateTime.strftime('%p').lower()
            tmpTimeStr = eventStartDateTime.strftime('%l:%M') + meridiem
            message += '%s  %s\n' % (tmpTimeStr, event.title.text)

        if (message == ''):
            return

        message = "Google Calendar Reminder:\n" + message

        cmd = shlex.split(command)

        for i, a in zip(xrange(len(cmd)), cmd):
            if (a == '%s'):
                cmd[i] = message

        pid = os.fork()
        if not pid:
            os.execvp(cmd[0], cmd)


def LoadConfig(configFile):

    config = ConfigParser()
    config.read(os.path.expanduser(configFile))
    return config


def GetConfig(config, key, default):

    try:
        value = config.get('gcalcli', key)
    except:
        value = default

    return value


def GetTrueFalse(value):

    if (value.lower() == 'false'): return False
    else: return True


def GetColor(value):

    colors = { 'default'       : CLR_NRM(),
               'black'         : CLR_BLK(),
               'brightblack'   : CLR_BRBLK(),
               'red'           : CLR_RED(),
               'brightred'     : CLR_BRRED(),
               'green'         : CLR_GRN(),
               'brightgreen'   : CLR_BRGRN(),
               'yellow'        : CLR_YLW(),
               'brightyellow'  : CLR_BRYLW(),
               'blue'          : CLR_BLU(),
               'brightblue'    : CLR_BRBLU(),
               'magenta'       : CLR_MAG(),
               'brightmagenta' : CLR_BRMAG(),
               'cyan'          : CLR_CYN(),
               'brightcyan'    : CLR_BRCYN(),
               'white'         : CLR_WHT(),
               'brightwhite'   : CLR_BRWHT() }

    try:
        return colors[value]
    except:
        PrintErrMsg('\nError: invalid color name\n')
        Usage()


def DoooooItHippieMonster():

    try:
        opts, args = getopt.getopt(sys.argv[1:], "",
                                   ["config=",
                                    "user=",
                                    "pw=",
                                    "cals=",
                                    "cal=",
                                    "details",
                                    "ignore-started",
                                    "width=",
                                    "mon",
                                    "nc",
                                    "cal-owner-color=",
                                    "cal-editor-color=",
                                    "cal-contributor-color=",
                                    "cal-read-color=",
                                    "cal-freebusy-color=",
                                    "date-color=",
                                    "border-color="])
    except getopt.error:
        Usage()

    configFile = '~/.gcalclirc'

    # look for config file override then load the config file
    # we do this first because command line args take precedence
    for opt, arg in opts:
        if (opt == "--config"): configFile = arg

    cfg = LoadConfig(configFile)

    usr           = GetConfig(cfg, 'user', __username__)
    pwd           = GetConfig(cfg, 'pw', __password__)
    access        = GetConfig(cfg, 'cals', 'all')
    workCalNames  = [ GetConfig(cfg, 'cal', None) ]
    details       = GetTrueFalse(GetConfig(cfg, 'details', 'false'))
    ignoreStarted = GetTrueFalse(GetConfig(cfg, 'ignore-started', 'false'))
    calWidth      = int(GetConfig(cfg, 'width', '10'))
    #calMonday     = GetTrueFalse(GetConfig(cfg, 'mon', 'false'))
    calMonday     = False

    calOwnerColor       = GetColor(GetConfig(cfg, 'cal-owner-color', 'cyan'))
    calEditorColor      = GetColor(GetConfig(cfg, 'cal-editor-color', 'green')) 
    calContributorColor = GetColor(GetConfig(cfg, 'cal-contributor-color', 'default'))
    calReadColor        = GetColor(GetConfig(cfg, 'cal-read-color', 'magenta'))
    calFreeBusyColor    = GetColor(GetConfig(cfg, 'cal-freebusy-color', 'default'))
    dateColor           = GetColor(GetConfig(cfg, 'date-color', 'yellow'))
    borderColor         = GetColor(GetConfig(cfg, 'border-color', 'white'))

    # fix wokCalNames when not specified in config file
    if ((len(workCalNames) == 1) and (workCalNames[0] == None)):
        workCalNames = []

    # Process options
    for opt, arg in opts:
        if (opt == "--help"): Usage()
        elif (opt == "--user"): usr = arg
        elif (opt == "--pw"): pwd = arg
        elif (opt == "--cals"): access = arg
        elif (opt == "--cal"): workCalNames.append(arg)
        elif (opt == "--details"): details = True
        elif (opt == "--ignore-started"): ignoreStarted = True
        elif (opt == "--width"): calWidth = int(arg)
        elif (opt == "--mon"): Usage() #calMonday = True # not ready yet...)
        elif (opt == "--nc"): CLR.useColor = False
        elif (opt == "--cal-owner-color"): calOwnerColor = GetColor(arg)
        elif (opt == "--cal-editor-color"): calEditorColor = GetColor(arg)
        elif (opt == "--cal-contributor-color"): calContributorColor = GetColor(arg)
        elif (opt == "--cal-read-color"): calReadColor = GetColor(arg)
        elif (opt == "--cal-freebusy-color"): calFreeBusyColor = GetColor(arg)
        elif (opt == "--date-color"): dateColor = GetColor(arg)
        elif (opt == "--border-color"): borderColor = GetColor(arg)

    if ((usr == '') or (pwd == '')):
        PrintErrMsg('\nError: must specify username and password\n')
        Usage()

    if (len(args) == 0):
        PrintErrMsg('\nError: no command\n')
        Usage()

    gcal = GoogleCalendar(username=usr,
                          password=pwd,
                          access=access,
                          workCalNames=workCalNames,
                          details=details,
                          ignoreStarted=ignoreStarted,
                          calWidth=calWidth,
                          calMonday=calMonday,
                          calOwnerColor=calOwnerColor,
                          calEditorColor=calEditorColor,
                          calContributorColor=calContributorColor,
                          calReadColor=calReadColor,
                          calFreeBusyColor=calFreeBusyColor,
                          dateColor=dateColor,
                          borderColor=borderColor)

    if (args[0] == 'list'):
        gcal.ListAllCalendars()

    elif (args[0] == 'search'):
        if (len(args) != 2):
            PrintErrMsg('\nError: invalid search string\n')
            Usage()
        # allow unicode strings for input
        uniArg = unicode(args[1], locale.getpreferredencoding())
        gcal.TextQuery(uniArg)

    elif (args[0] == 'agenda'):
        if (len(args) == 3):   # start and end
            gcal.AgendaQuery(startText=args[1], endText=args[2])
        elif (len(args) == 2): # start
            gcal.AgendaQuery(startText=args[1])
        elif (len(args) == 1): # defaults
            gcal.AgendaQuery()
        else:
            PrintErrMsg('\nError: invalid agenda arguments\n')
            Usage()

    elif (args[0] == 'calw'):
        if not calWidth:
            PrintErrMsg('\nError: invalid width, don\'t be an idiot!\n')
            Usage()

        if (len(args) >= 2):
            try:
                count = int(args[1])
            except:
                PrintErrMsg('\nError: invalid calw arguments\n')
                Usage()

        if (len(args) == 3):   # weeks and start
            gcal.CalQuery(args[0], count=int(args[1]), startText=args[2])
        elif (len(args) == 2): # weeks
            gcal.CalQuery(args[0], count=int(args[1]))
        elif (len(args) == 1): # defaults
            gcal.CalQuery(args[0])
        else:
            PrintErrMsg('\nError: invalid calw arguments\n')
            Usage()

    elif (args[0] == 'calm'):
        if not calWidth:
            PrintErrMsg('\nError: invalid width, don\'t be an idiot!\n')
            Usage()

        if (len(args) == 2): # start
            gcal.CalQuery(args[0], startText=args[1])
        elif (len(args) == 1): # defaults
            gcal.CalQuery(args[0])
        else:
            PrintErrMsg('\nError: invalid calm arguments\n')
            Usage()

    elif (args[0] == 'quick'):
        if (len(args) != 2):
            PrintErrMsg('\nError: invalid event text\n')
            Usage()

        # allow unicode strings for input
        uniArg = unicode(args[1], locale.getpreferredencoding())
        gcal.QuickAdd(uniArg)
        return

    elif (args[0] == 'remind'):
        if (len(args) == 3):   # minutes and command
            gcal.Remind(int(args[1]), args[2])
        elif (len(args) == 2): # minutes
            gcal.Remind(int(args[1]))
        elif (len(args) == 1): # defaults
            gcal.Remind()
        else:
            PrintErrMsg('\nError: invalid remind arguments\n')
            Usage()
        return

    else:
        PrintErrMsg('\nError: unknown command\n')
        Usage()

    sys.stdout.write('\n')


if __name__ == '__main__':
    DoooooItHippieMonster()

