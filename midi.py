import tkinter as tk
from pygame import midi


class MIDIKeyboard(tk.Frame):
    MIDI_STATE_PRESSED = 144
    MIDI_STATE_RELEASED = 128
    MIDI_STATE_SUSTAIN = 176

    BLACK_KEYS = [1, 3, 6, 8, 10]
    WHITE_KEYS = [0, 2, 4, 5, 7, 9, 11]

    WHITE_KEYS_PER_OCTAVE = len(WHITE_KEYS)
    BLACK_KEYS_PER_OCTAVE = len(BLACK_KEYS)

    KEYS_PER_OCTAVE = WHITE_KEYS_PER_OCTAVE+BLACK_KEYS_PER_OCTAVE

    LOWEST_KEY = 0
    HIGHEST_KEY = 120

    KEYS_TO_ID = {
        "a": 48,
        "w": 49,
        "s": 50,
        "e": 51,
        "d": 52,
        "f": 53,
        "t": 54,
        "g": 55,
        "z": 56,
        "h": 57,
        "u": 58,
        "j": 59,
        "k": 60,
    }
    KEY_SUSTAIN = " "

    # Checks

    def _key_is_black(self, keyid):
        return (keyid % self.KEYS_PER_OCTAVE) in self.BLACK_KEYS

    # Init

    def __init__(self, root, octave_start=4, octaves=2, width=None, height=200):
        super().__init__(root)

        self._root = root
        self._root.bind('<KeyPress>', self._tkinter_key_pressed)
        self._root.bind('<KeyRelease>', self._tkinter_key_released)

        self._height = height
        self._width = width or ((octaves*self.WHITE_KEYS_PER_OCTAVE) * 30)
        width_per_key = int(self._width/(octaves*self.WHITE_KEYS_PER_OCTAVE))

        self._canvas = tk.Canvas(
            root, width=self._width, height=self._height, bg="#FFFFFF")
        self._canvas.pack(side="top", fill="both", expand=True)

        self._keys = {}

        for o in range(octaves):
            bk = 0
            for k in range(self.KEYS_PER_OCTAVE):
                keyid = ((octave_start+o)*self.KEYS_PER_OCTAVE)+k

                if self._key_is_black(k):
                    x_start = int(
                        (o*self.WHITE_KEYS_PER_OCTAVE+(k-0.25-bk))*width_per_key)
                    x_end = int((o*self.WHITE_KEYS_PER_OCTAVE +
                                 (k+0.25-bk))*width_per_key)

                    rectid = self._canvas.create_rectangle(
                        x_start, 0, x_end, self._height/2, fill="#000000", outline="#000000", tags=f"key blackkey key_{keyid}")
                    bk += 1
                else:
                    x_start = int(
                        (o*self.WHITE_KEYS_PER_OCTAVE+(k-bk))*width_per_key)
                    x_end = int(
                        (o*self.WHITE_KEYS_PER_OCTAVE+(k+1-bk))*width_per_key)
                    rectid = self._canvas.create_rectangle(
                        x_start, 0, x_end, self._height, fill="#FFFFFF", outline="#000000", tags=f"key whitekey key_{keyid}")

                self._keys[keyid] = rectid
                self._canvas.tag_bind(
                    rectid, "<Button-1>", self._tkinter_mouse_pressed)
                self._canvas.tag_bind(
                    rectid, "<ButtonRelease-1>", self._tkinter_mouse_released)
                self._canvas.tag_bind(
                    rectid, "<B1-Motion>", self._tkinter_motion)

        self._canvas.tag_raise("blackkey")
        self._keys_inverted = {v: k for k, v in self._keys.items()}

        self._tkinter_last_keyid = None

    # UI Updates

    def _update_key(self, keyid, pressed, velocity=127):
        print("Key", keyid, pressed, velocity)
        color = hex(255-(velocity*2)).split("x")[1].zfill(2)
        if keyid is None:
            return
        elif keyid >= self.LOWEST_KEY and keyid <= self.HIGHEST_KEY:
            if keyid in self._keys:
                self._canvas.itemconfig(
                    self._keys[keyid], fill=f"#00ff{color}" if pressed else "#000000" if self._key_is_black(keyid) else "#ffffff")
            if self._midi_out:
                if pressed:
                    self._midi_out.note_on(keyid, velocity)
                else:
                    self._midi_out.note_off(keyid, velocity)
        else:
            print("Key out of range:", keyid)

    def _update_sustain(self, velocity, channel=0):
        print("Sustain", velocity)
        if self._midi_out:
            self._midi_out.write_short(0xb0 + channel, 64, velocity)

    # Tkinter Events

    def _tkinter_get_key_at_pos(self, event):
        if event.x >= 0 and event.x <= self._width and event.y >= 0 and event.y <= self._height:
            rectid = event.widget.find_closest(event.x, event.y)[0]
            return self._keys_inverted[rectid]
        else:
            return None

    def _tkinter_mouse_pressed(self, event):
        keyid = self._tkinter_get_key_at_pos(event)
        self._update_key(keyid, True)
        self._tkinter_last_keyid = keyid

    def _tkinter_mouse_released(self, event):
        self._update_key(self._tkinter_last_keyid, False)

    def _tkinter_motion(self, event):
        keyid = self._tkinter_get_key_at_pos(event)
        if not self._tkinter_last_keyid == keyid:
            self._update_key(self._tkinter_last_keyid, False)
            self._tkinter_last_keyid = keyid
            self._update_key(self._tkinter_last_keyid, True)

    def _tkinter_key_pressed(self, event):
        if event.char in self.KEYS_TO_ID:
            self._update_key(self.KEYS_TO_ID[event.char], True)
        elif event.char == self.KEY_SUSTAIN:
            self._update_sustain(127)

    def _tkinter_key_released(self, event):
        if event.char in self.KEYS_TO_ID:
            self._update_key(self.KEYS_TO_ID[event.char], False)
        elif event.char == self.KEY_SUSTAIN:
            self._update_sustain(0)

    # Midi Events

    def _parse_midi_event(self, event, highervelocity=False):
        state = event[0][0]
        key = event[0][1]
        velocity = event[0][2]

        print(event)

        if state == self.MIDI_STATE_PRESSED:
            velocity = int(event[0][2]/2)+64 if highervelocity else velocity
            self._update_key(key, True, velocity)
        elif state == self.MIDI_STATE_RELEASED:
            self._update_key(key, False, velocity)
        elif state == self.MIDI_STATE_SUSTAIN:
            self._update_sustain(velocity)
        else:
            print("Unknown event!", event[0])

    # Main

    def mainloop(self, inputdeviceid=None, outputdeviceid=None, ignoreerror=False, highervelocity=False):
        midi.init()

        try:
            inputdeviceid = inputdeviceid if inputdeviceid is not None else midi.get_default_input_id()
            print("MIDI Input:", midi.get_device_info(inputdeviceid))
            self._midi_in = midi.Input(inputdeviceid)
        except midi.MidiException as e:
            if ignoreerror:
                self._midi_in = None
            else:
                raise e

        try:
            outputdeviceid = outputdeviceid if outputdeviceid is not None else midi.get_default_output_id()
            print("MIDI Output:", midi.get_device_info(outputdeviceid))
            self._midi_out = midi.Output(outputdeviceid)
            self._midi_out.set_instrument(0)
        except (midi.MidiException, Exception) as e:
            if ignoreerror:
                self._midi_out = None
            else:
                raise e

        if self._midi_in:
            while True:
                if self._midi_in.poll():
                    events = self._midi_in.read(10)
                    for event in events:
                        self._parse_midi_event(
                            event, highervelocity=highervelocity)
                try:
                    self._root.update()
                except:
                    midi.quit()
                    break
        else:
            self._root.mainloop()


def midiinfo():
    midi.init()
    print()
    for i in range(midi.get_count()):
        print(i, midi.get_device_info(i))
    print()


midiinfo()

root = tk.Tk()
root.title("MIDI Keyboard")

kb = MIDIKeyboard(root, octave_start=3, octaves=4, width=1200)
kb.pack(side="top", fill="both", expand=True)
kb.mainloop(outputdeviceid=0, ignoreerror=True, highervelocity=True)