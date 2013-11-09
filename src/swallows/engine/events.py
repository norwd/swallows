#!/usr/bin/env python

import random
import sys

from swallows.util import pick

# TODO

# Diction:
# the event-accumulation framework could use rewriting at some point.
# eliminate identical duplicate sentences
# Bob is in the dining room & "Bob made his way to the dining room" ->
#  "Bob wandered around for a bit, then came back to the dining room"
# a better solution for "Bob was in the kitchen" at the start of a paragraph;
#   this might include significant memories Bob acquired in the last
#   paragraph -- such as finding a revolver in the bed
# paragraphs should not always be the same number of events.  variety!
# the Editor should take all the events in the chapter, and decide where
#   paragraph breaks should go.  this is difficult, because syncing up
#   Bob's and Alice's events.  timestamps?
# at least, the Editor should record "rich events", which include information
#   about the main (acting) character, and where the audience last saw them
# use indef art when they have no memory of an item that they see
# dramatic irony would be really nice, but hard to pull off.  Well, a certain
#  amount happens naturally now, with character pov.  but more could be done
# "Chapter 3.  _In which Bob hides the stolen jewels in the mailbox, etc_" --
#  i.e. chapter summaries -- that's a little too fancy to hope for, but with
#  a sufficiently smart Editor it could be done

### EVENTS ###

class Event(object):
    def __init__(self, phrase, participants, excl=False):
        """participants[0] is always the initiator, and we
        record the location that the event was initiated in.

        For now, we assume such an event can be:
        - observed by every actor at that location
        - affects only actors at that location

        In the future, we *may* have:
        - active and passive participants
        - active participants all must be present at the location
        - passive participants need not be
        (probably done by passing a number n: the first n
        participants are to be considered active)

        """
        self.phrase = phrase
        self.participants = participants
        self.location = participants[0].location
        self.excl = excl

    def initiator(self):
        return self.participants[0]

    def __str__(self):
        phrase = self.phrase
        i = 0
        for participant in self.participants:
            phrase = phrase.replace('<%d>' % (i + 1), participant.render(self.participants))
            phrase = phrase.replace('<indef-%d>' % (i + 1), participant.indefinite())
            phrase = phrase.replace('<his-%d>' % (i + 1), participant.posessive())
            phrase = phrase.replace('<him-%d>' % (i + 1), participant.accusative())
            phrase = phrase.replace('<he-%d>' % (i + 1), participant.pronoun())
            phrase = phrase.replace('<was-%d>' % (i + 1), participant.was())
            phrase = phrase.replace('<is-%d>' % (i + 1), participant.is_())
            i = i + 1
        if self.excl:
            phrase = phrase + '!'
        else:
            phrase = phrase + '.'
        return phrase[0].upper() + phrase[1:]


class EventCollector(object):
    def __init__(self):
        self.events = []
    
    def collect(self, event):
        self.events.append(event)

    def dedup(self):
        """Modifies the sequence of events so that the same event
        does not occur multiple times in a row.

        """
        if len(self.events) <= 1:
            return
        events = [self.events[0]]
        for event in self.events[1:]:
            if str(event) != str(events[-1]):
                events.append(event)
        self.events = events
        

# not really needed, as emit() does nothing if there is no collector
class Oblivion(EventCollector):
    def collect(self, event):
        pass


oblivion = Oblivion()


# 'diction engine' -- almost exactly like a peephole optimizer -- convert
#   "Bob went to the shed.  Bob saw Alice." into
#   "Bob went to the shed, where he saw Alice."
# btw, it doesn't do that exact example yet.
# btw, we currently get a new editor for every paragraph
class LegacyEditor(object):
    """The LegacyEditor is remarkably similar to the _peephole optimizer_ in
    compiler construction.  Instead of replacing sequences of instructions
    with more efficient but semantically equivalent sequences of
    instructions, it replaces sequences of sentences with more readable
    but semantically equivalent sequences of sentences.

    """
    MEMORY = 1

    def __init__(self):
        self.character = None
        self.character_location = {}
        self.events = []

    def read(self, event):
        if len(self.events) < self.__class__.MEMORY:
            self.events.append(event)
            return

        character = event.participants[0]
        # update our idea of their location
        self.character_location[character.name] = character.location
        # todo: check our idea of their location vs where they are,
        # but that won't matter until an editor looks at more than one
        # paragraph anyway

        if character == self.character:  # same character doing stuff        
            if event.phrase.startswith('<1>'):
                event.phrase = '<he-1>' + event.phrase[3:]

            if (self.events[-1].phrase == '<1> made <his-1> way to <2>' and
                event.phrase == '<1> went to <2>'):
                self.events[-1].participants[1] = event.participants[1]
            elif (self.events[-1].phrase == '<1> went to <2>' and
                event.phrase == '<1> went to <2>'):
                self.events[-1].phrase = '<1> made <his-1> way to <2>'
                self.events[-1].participants[1] = event.participants[1]
            elif (self.events[-1].phrase == '<he-1> made <his-1> way to <2>' and
                event.phrase == '<he-1> went to <2>'):
                self.events[-1].participants[1] = event.participants[1]
            elif (self.events[-1].phrase == '<he-1> went to <2>' and
                event.phrase == '<he-1> went to <2>'):
                self.events[-1].phrase = '<he-1> made <his-1> way to <2>'
                self.events[-1].participants[1] = event.participants[1]
            else:
                self.events.append(event)
        else:  # new character doing stuff
            self.character = character
            self.events.append(event)


class LegacyPublisher(object):
    """Publisher which uses the old Event/Editor framework.

    Will probably go away eventually, but nice to have as a reference
    while working on the new Event/Editor framework.

    """
    def __init__(self, **kwargs):
        self.characters = kwargs.get('characters')
        self.setting = kwargs.get('setting')
        self.friffery = kwargs.get('friffery', False)
        self.debug = kwargs.get('debug', False)
        self.title = kwargs.get('title', "Untitled")
        self.chapters = kwargs.get('chapters', 16)
        self.paragraphs_per_chapter = kwargs.get('paragraphs_per_chapter', 25)

    def publish(self):
        print self.title
        print "=" * len(self.title)
        print

        for chapter in range(1, self.chapters+1):
            print "Chapter %d." % chapter
            print "-----------"
            print

            for character in self.characters:
                # don't continue a conversation from the previous chapter, please
                character.topic = None
                character.location = None
        
            for paragraph in range(1, self.paragraphs_per_chapter+1):
                for character in self.characters:
                    character.collector = EventCollector()

                # we alternate pov like so:
                pov_actor = (self.characters)[(paragraph - 1) % len(self.characters)]

                for actor in self.characters:
                    if actor.location is None:
                        actor.place_in(pick(self.setting))
                    else:
                        # this is hacky & won't work for >2 characters:
                        if self.characters[0].location is not self.characters[1].location:
                            actor.emit("<1> was in <2>", [actor, actor.location])

                while len(pov_actor.collector.events) < 20:
                    for actor in self.characters:
                        actor.live()

                if self.friffery:
                    if paragraph == 1:
                        choice = random.randint(0, 3)
                        if choice == 0:
                            sys.stdout.write("It was raining.  ")
                        if choice == 1:
                            sys.stdout.write("It was snowing.  ")
                        if choice == 2:
                            sys.stdout.write("The sun was shining.  ")
                        if choice == 3:
                            sys.stdout.write("The day was overcast and humid.  ")
                    elif not str(c.events[0]).startswith("'"):
                        choice = random.randint(0, 8)
                        if choice == 0:
                            sys.stdout.write("Later on, ")
                        if choice == 1:
                            sys.stdout.write("Suddenly, ")
                        if choice == 2:
                            sys.stdout.write("After a moment's consideration, ")
                        if choice == 3:
                            sys.stdout.write("Feeling anxious, ")
        
                if self.debug:
                    for character in self.characters:
                        print "%s'S POV:" % character.name.upper()
                        for event in character.collector.events:
                            print str(event)
                        print
                        character.dump_memory()
                        print
                    print "- - - - -"
                    print
        
                if not self.debug:
                    editor = LegacyEditor()
                    for event in pov_actor.collector.events:
                        editor.read(event)
                    for event in editor.events:
                        sys.stdout.write(str(event) + "  ")
                        #sys.stdout.write("\n")
                    print
                    print


### the new stuff ###

class Editor(object):
    """The Editor is remarkably similar to the _peephole optimizer_ in
    compiler construction.  Instead of replacing sequences of instructions
    with more efficient but semantically equivalent sequences of
    instructions, it replaces sequences of sentences with more readable
    but semantically equivalent sequences of sentences.

    The Editor is also responsible for chopping up the sequence of
    sentences into "sensible" paragraphs.  (This might be like a compiler
    code-rewriting pass that inserts NOPs to ensure instructions are on a
    word boundary, or some such.)
    
    The Editor is also responsible for picking which character to
    follow.  (I don't think there's a compiler construction analogy for
    that.)

    """
 
    def __init__(self, collector, main_characters):
        # This dedup'ing is temporary.
        # Eventually, we will dedup at the source (the Actors which
        # are currently producing redundant events.)
        collector.dedup()
        self.events = list(reversed(collector.events))
        self.main_characters = main_characters
        self.pov_index = 0

    def publish(self):
        # yoiks.  i have very little idea what I'm doing
        # XXX this gets duplicates because we are producing duplicates in
        # the engine because the engine assumes each actor has its own
        # event collector which is no longer the case.
        # XXX fix for now by deduping the event stream... somewhere...
        while len(self.events) > 0:
            pov_actor = self.main_characters[self.pov_index]
            self.publish_paragraph(pov_actor)
            self.pov_index += 1
            if self.pov_index >= len(self.main_characters):
                self.pov_index = 0

    def publish_paragraph(self, pov_actor):
        sentences_to_go = 10
        while sentences_to_go > 0 and len(self.events) > 0:
            event = self.events.pop()
            sentences_produced = self.consume(event, pov_actor)
            sentences_to_go -= sentences_produced
        print
        print

    def consume(self, event, pov_actor):
        """Returns how many sentences it produced.

        """
        if False:  # debug
            print "%r in %s: %s" % (
                [p.render([]) for p in event.participants],
                event.location.render([]),
                event.phrase
            )
            return 1
        else:
            if event.participants[0] is pov_actor:
                sys.stdout.write(str(event) + "  ")
                sys.stdout.write("\n")
                return 1
            else:
                return 0


class Publisher(object):
    def __init__(self, **kwargs):
        self.characters = kwargs.get('characters')
        self.setting = kwargs.get('setting')
        self.friffery = kwargs.get('friffery', False)
        self.debug = kwargs.get('debug', False)
        self.title = kwargs.get('title', "Untitled")
        self.chapters = kwargs.get('chapters', 16)
        self.events_per_chapter = kwargs.get('events_per_chapter', 50)

    def publish_chapter(self, chapter_num):

        collector = EventCollector()
        
        for actor in self.characters:
            actor.collector = collector
            # don't continue a conversation from the previous chapter, please
            actor.topic = None
            actor.location = None
            actor.place_in(pick(self.setting))

        while len(collector.events) < self.events_per_chapter:
            for actor in self.characters:
                actor.live()
                #print len(collector.events) # , repr([str(e) for e in collector.events])

        if self.debug:
            for character in self.characters:
                print "%s'S POV:" % character.name.upper()
                for event in character.collector.events:
                    print str(event)
                print
                character.dump_memory()
                print
            print "- - - - -"
            print
        else:
            editor = Editor(collector, self.characters)
            editor.publish()

    def publish(self):
        print self.title
        print "=" * len(self.title)
        print

        for chapter in range(1, self.chapters+1):
            print "Chapter %d." % chapter
            print "-----------"
            print

            self.publish_chapter(chapter)
