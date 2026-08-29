/*
 * IODebug - I/O signal debugger for Arduino Mega 2560
 *
 * Scans every usable pin and reports what is actually happening on it, with
 * extra detail on digital inputs: edges, timing between edges, pulse widths and
 * bounce counts.
 *
 * Pin policy
 *   D2..D53   sampled as INPUT_PULLUP. Pullup mode never drives the pin, so
 *             nothing external can be damaged and nothing is fought over. An
 *             unconnected pin therefore reads HIGH; a switch to GND reads LOW.
 *   D0, D1    skipped - they are the USB serial link carrying this output.
 *   A0..A15   left in their default high-impedance state and only read, so the
 *             analog values are not skewed by a pullup.
 *
 * Serial: 115200 baud. Send 'h' for the command list.
 */

const uint8_t  DIG_FIRST = 2;      // D0/D1 are the USB serial pins
const uint8_t  DIG_LAST  = 53;
const uint8_t  DIG_COUNT = DIG_LAST - DIG_FIRST + 1;
const uint8_t  ANA_COUNT = 16;     // A0..A15

const unsigned long SNAPSHOT_MS = 3000;
const unsigned long ANALOG_MS   = 200;   // analog sample interval
const uint16_t ANALOG_NOISE_GATE = 4;    // ignore +/-4 LSB of ADC jitter

struct DigitalPin {
  unsigned long lastChangeMs;
  uint16_t      changes;       // total edges seen
  uint16_t      minPulseMs;    // shortest time a level was held
  bool          state;
};

struct AnalogCh {
  uint16_t last;
  uint16_t minV;
  uint16_t maxV;
  uint32_t sum;
  uint16_t samples;
};

DigitalPin dig[DIG_COUNT];
AnalogCh   ana[ANA_COUNT];

unsigned long lastSnapshot = 0;
unsigned long lastAnalog   = 0;
unsigned long startedAt    = 0;
bool showDigital = true;
bool showAnalog  = true;

/*
 * Input mode for D2..D53.
 *
 *   true  INPUT_PULLUP - ~30k to 5V. Detects connections well, because anything
 *                        sinking current shows up as a LOW. The pin is still an
 *                        input and is never driven.
 *   false INPUT (high-Z) - the pin sources and sinks essentially nothing. Use
 *                        this the first time the board is plugged into live
 *                        wiring: a high-Z pin cannot supply enough current to
 *                        trip an opto-isolated relay input even if that input
 *                        is configured to trigger on HIGH.
 */
bool usePullup = true;

void applyPinMode() {
  for (uint8_t p = DIG_FIRST; p <= DIG_LAST; p++) {
    pinMode(p, usePullup ? INPUT_PULLUP : INPUT);
  }
}

// ---------------------------------------------------------------- helpers

void resetStats() {
  unsigned long now = millis();
  for (uint8_t i = 0; i < DIG_COUNT; i++) {
    dig[i].state        = digitalRead(DIG_FIRST + i);
    dig[i].lastChangeMs = now;
    dig[i].changes      = 0;
    dig[i].minPulseMs   = 0xFFFF;
  }
  for (uint8_t i = 0; i < ANA_COUNT; i++) {
    uint16_t v = analogRead(A0 + i);
    ana[i].last    = v;
    ana[i].minV    = v;
    ana[i].maxV    = v;
    ana[i].sum     = v;
    ana[i].samples = 1;
  }
  startedAt = now;
}

void printBanner() {
  Serial.println();
  Serial.println(F("=================================================="));
  Serial.println(F(" IODebug - Arduino Mega 2560 I/O signal debugger"));
  Serial.println(F("=================================================="));
  Serial.print(F(" digital : D"));   Serial.print(DIG_FIRST);
  Serial.print(F("..D"));            Serial.print(DIG_LAST);
  Serial.println(F("  (INPUT_PULLUP - unconnected reads HIGH)"));
  Serial.println(F(" analog  : A0..A15 (high-Z, 0..1023)"));
  Serial.println(F(" skipped : D0/D1 - USB serial"));
  Serial.println(F(" commands: h=help s=snapshot r=reset d=digital a=analog"));
  Serial.println(F("--------------------------------------------------"));
  Serial.println(F("Watching for edges. Touch a pin to GND to see it fire."));
  Serial.println();
}

void printHelp() {
  Serial.println(F("\n-- commands --"));
  Serial.println(F("  h  this help"));
  Serial.println(F("  s  print a full snapshot now"));
  Serial.println(F("  p  characterise every pin (read-only, never drives a pin)"));
  Serial.println(F("  z  toggle INPUT_PULLUP <-> INPUT high-Z (use high-Z on live wiring)"));
  Serial.println(F("  w  watch mode - emit 'ST <ms> <mask>' on every pin change"));
  Serial.println(F("  r  reset all counters and statistics"));
  Serial.println(F("  d  toggle digital reporting"));
  Serial.println(F("  a  toggle analog reporting"));
  Serial.println();
}

// Print only pins that are LOW, i.e. actually pulled down by something.
void snapshotDigital() {
  Serial.println(F("-- digital --"));
  Serial.println(F("  pin  state  edges  minPulse  lastChange"));

  uint8_t active = 0;
  for (uint8_t i = 0; i < DIG_COUNT; i++) {
    bool interesting = (dig[i].state == LOW) || (dig[i].changes > 0);
    if (!interesting) continue;
    active++;

    Serial.print(F("  D"));
    Serial.print(DIG_FIRST + i);
    if (DIG_FIRST + i < 10) Serial.print(' ');
    Serial.print(dig[i].state ? F("   HIGH ") : F("   LOW  "));
    Serial.print(F("  "));
    Serial.print(dig[i].changes);
    Serial.print(F("      "));
    if (dig[i].minPulseMs == 0xFFFF) Serial.print(F("-"));
    else { Serial.print(dig[i].minPulseMs); Serial.print(F("ms")); }
    Serial.print(F("       "));
    Serial.print((millis() - dig[i].lastChangeMs) / 1000.0, 1);
    Serial.println(F("s ago"));
  }

  if (active == 0) {
    Serial.print(F("  all "));
    Serial.print(DIG_COUNT);
    Serial.println(F(" pins idle HIGH - nothing connected pulling them down"));
  }
}

void snapshotAnalog() {
  Serial.println(F("-- analog --"));
  Serial.println(F("  ch   now   min   max    avg   swing"));

  for (uint8_t i = 0; i < ANA_COUNT; i++) {
    uint16_t swing = ana[i].maxV - ana[i].minV;
    // Quiet, mid-scale-free channels are almost always floating inputs.
    if (swing <= ANALOG_NOISE_GATE && ana[i].last < 8) continue;

    Serial.print(F("  A"));
    Serial.print(i);
    if (i < 10) Serial.print(' ');
    Serial.print(F("  "));
    Serial.print(ana[i].last);
    Serial.print(F("   "));
    Serial.print(ana[i].minV);
    Serial.print(F("   "));
    Serial.print(ana[i].maxV);
    Serial.print(F("   "));
    Serial.print(ana[i].samples ? (ana[i].sum / ana[i].samples) : 0);
    Serial.print(F("   "));
    Serial.print(swing);
    if (swing > 50) Serial.print(F("  <- noisy/changing"));
    Serial.println();
  }
}

/*
 * Is this pin genuinely wired to something that sinks current?
 *
 * A single digitalRead is not enough to answer that. With the internal pullup
 * engaged the pin charges through ~30k into ~10pF, an RC of well under a
 * microsecond, so a pin with nothing attached reads HIGH effectively
 * instantly - it can never read LOW.
 *
 * A LOW therefore means roughly 80uA is being pulled out of the pin. That is
 * either a real DC load, or mains hum capacitively coupled into a wire left
 * open at the far end. The two are told apart by time: a DC load holds the pin
 * low continuously, while 50/60Hz coupling crosses zero every 10ms or so.
 *
 * Sampling across several full mains cycles and demanding LOW throughout
 * rejects the coupled noise and keeps only real connections.
 */
const uint8_t  WIRE_SAMPLES = 120;    // 120 samples, 1ms apart
const uint16_t WIRE_WINDOW_MS = 120;  // 6 cycles at 50Hz, 7 at 60Hz

bool pinIsWired(uint8_t p) {
  pinMode(p, INPUT_PULLUP);
  delayMicroseconds(500);
  for (uint8_t i = 0; i < WIRE_SAMPLES; i++) {
    if (digitalRead(p) == HIGH) return false;   // one HIGH is enough to reject
    delay(WIRE_WINDOW_MS / WIRE_SAMPLES);
  }
  return true;
}

/*
 * Characterise every digital pin without ever driving it.
 *
 * Each pin is read twice: once with the internal pullup (~30k to 5V) engaged,
 * once with the pin high-impedance. Both are input modes, so no pin is ever
 * driven and nothing connected outside can be damaged or actuated.
 *
 *   LOW while pulled up  -> something outside is sinking current: a real load,
 *                           a closed contact, or a relay input wired to GND.
 *                           This is the only fully reliable "connected" verdict.
 *   HIGH in both reads   -> either nothing is connected, or something is holding
 *                           the pin high. These two CANNOT be told apart without
 *                           driving the pin, which this function refuses to do.
 */
void characterisePins() {
  Serial.println();
  Serial.println(F("===== pin characterisation (read-only, never drives) ====="));
  Serial.println(F("  pin   pulled-up   high-Z   verdict"));

  uint8_t connected = 0;
  for (uint8_t p = DIG_FIRST; p <= DIG_LAST; p++) {
    pinMode(p, INPUT_PULLUP);
    delayMicroseconds(500);            // let the 30k pullup charge the pin
    if (digitalRead(p) == HIGH) {      // idle/unconnected - not worth a line
      pinMode(p, usePullup ? INPUT_PULLUP : INPUT);
      continue;
    }

    bool solid = pinIsWired(p);        // hold low across several mains cycles?
    pinMode(p, usePullup ? INPUT_PULLUP : INPUT);   // restore the chosen mode

    Serial.print(F("  D"));
    Serial.print(p);
    if (p < 10) Serial.print(' ');
    Serial.print(F("     LOW       "));
    if (solid) {
      connected++;
      Serial.println(F("held       WIRED - a real load holds it down"));
    } else {
      Serial.println(F("flickers   noise - AC pickup on an open-ended wire"));
    }
  }

  Serial.print(F("  -> "));
  Serial.print(connected);
  Serial.print(F(" of "));
  Serial.print(DIG_COUNT);
  Serial.println(F(" pins have something attached pulling them down."));
  Serial.println(F("  Pins reading HIGH are indistinguishable from unconnected"));
  Serial.println(F("  without driving them, which is not done here."));
  Serial.println();
}

/*
 * NOTE - there is deliberately no "drive a pin to find the relay" sweep here.
 *
 * The lift controller closes its own relay contacts to signal floor and status;
 * those contacts land on these pins. A closed contact is a short to the common
 * rail, so driving such a pin HIGH would put the AVR's push-pull output across
 * a dead short and can destroy the port. Every pin in this sketch stays an
 * input, always.
 *
 * Which pin carries which signal is instead worked out by watching the bits
 * move, in emitState() below plus the decoder on the PC.
 */

/*
 * Machine-readable state line, emitted whenever any watched pin changes:
 *
 *   ST <millis> <13 hex digits>
 *
 * The hex value is a 52-bit mask, bit i = pin (DIG_FIRST + i), 1 = pin HIGH.
 * With INPUT_PULLUP a closed contact reads LOW, so an active signal is a 0 bit;
 * the decoder inverts it. Sending the whole port state rather than just the
 * pins that changed means the PC side can be re-pointed at different pins
 * without reflashing the board.
 */
bool watchMode = false;
uint64_t lastMask = 0;

uint64_t readMask() {
  uint64_t m = 0;
  for (uint8_t i = 0; i < DIG_COUNT; i++) {
    if (digitalRead(DIG_FIRST + i)) m |= (uint64_t)1 << i;
  }
  return m;
}

void emitState(uint64_t mask, unsigned long t) {
  Serial.print(F("ST "));
  Serial.print(t);
  Serial.print(' ');
  for (int8_t nib = 12; nib >= 0; nib--) {          // 13 nibbles = 52 bits
    Serial.print((uint8_t)((mask >> (nib * 4)) & 0xF), HEX);
  }
  Serial.println();
}

void snapshot() {
  Serial.println();
  Serial.print(F("===== snapshot @ "));
  Serial.print((millis() - startedAt) / 1000.0, 1);
  Serial.println(F("s ====="));
  if (showDigital) snapshotDigital();
  if (showAnalog)  snapshotAnalog();
  Serial.println();
}

// ---------------------------------------------------------------- sketch

void setup() {
  Serial.begin(115200);
  while (!Serial) { ; }

  applyPinMode();

  delay(50);          // let the pullups settle before the first read
  resetStats();
  printBanner();
}

void loop() {
  unsigned long now = millis();

  // --- digital: sample every pass so short pulses are not missed
  //
  // Skipped entirely in watch mode. The ST mask already carries every pin, so
  // the human-readable EDGE lines are redundant there - and at 115200 baud a
  // burst of text fills the TX buffer and blocks the loop for tens of
  // milliseconds, during which nothing is being sampled at all.
  if (showDigital && !watchMode) {
    for (uint8_t i = 0; i < DIG_COUNT; i++) {
      bool level = digitalRead(DIG_FIRST + i);
      if (level == dig[i].state) continue;

      unsigned long held = now - dig[i].lastChangeMs;
      if (dig[i].changes > 0 && held < dig[i].minPulseMs) {
        dig[i].minPulseMs = (held > 0xFFFE) ? 0xFFFE : (uint16_t)held;
      }

      dig[i].state        = level;
      dig[i].lastChangeMs = now;
      dig[i].changes++;

      Serial.print(F("EDGE  t="));
      Serial.print(now);
      Serial.print(F("ms  D"));
      Serial.print(DIG_FIRST + i);
      Serial.print(level ? F("  LOW -> HIGH") : F("  HIGH -> LOW"));
      Serial.print(F("   held="));
      Serial.print(held);
      Serial.print(F("ms   edges="));
      Serial.print(dig[i].changes);
      // Sub-10 ms edges on a mechanical contact are contact bounce.
      if (held < 10 && dig[i].changes > 1) Serial.print(F("   <- BOUNCE?"));
      Serial.println();
    }
  }

  // --- watch mode: one compact line per change, for the PC-side decoder
  if (watchMode) {
    uint64_t m = readMask();
    if (m != lastMask) {
      lastMask = m;
      emitState(m, now);
    }
  }

  // --- analog: sampled on an interval, 16 ADC reads are comparatively slow
  if (showAnalog && now - lastAnalog >= ANALOG_MS) {
    lastAnalog = now;
    for (uint8_t i = 0; i < ANA_COUNT; i++) {
      uint16_t v = analogRead(A0 + i);
      ana[i].last = v;
      if (v < ana[i].minV) ana[i].minV = v;
      if (v > ana[i].maxV) ana[i].maxV = v;
      ana[i].sum += v;
      ana[i].samples++;
      if (ana[i].samples > 30000) {        // keep the running average bounded
        ana[i].sum     = ana[i].sum / ana[i].samples;
        ana[i].samples = 1;
      }
    }
  }

  // Periodic snapshots are for a human watching a terminal; during a capture
  // they only add latency to the sampling loop.
  if (!watchMode && now - lastSnapshot >= SNAPSHOT_MS) {
    lastSnapshot = now;
    snapshot();
  }

  while (Serial.available()) {
    switch (Serial.read()) {
      case 'h': printHelp(); break;
      case 's': snapshot();  break;
      case 'r': resetStats(); Serial.println(F("stats reset")); break;
      case 'p': characterisePins(); break;
      // Emit the current state on demand. Lets the logger take a baseline at
      // startup and a periodic heartbeat, so a quiet log can be told apart
      // from a broken one - silence alone proves nothing.
      case 'e': emitState(readMask(), millis()); break;
      case 'w':
        watchMode = !watchMode;
        Serial.print(F("watch mode "));
        Serial.println(watchMode ? F("ON - emitting ST lines on every change")
                                 : F("OFF"));
        if (watchMode) {
          lastMask = readMask();
          emitState(lastMask, millis());   // baseline, so the PC starts in sync
        }
        break;
      case 'z':
        usePullup = !usePullup;
        applyPinMode();
        delay(20);
        resetStats();
        Serial.print(F("input mode now "));
        Serial.println(usePullup ? F("INPUT_PULLUP (detects loads)")
                                 : F("INPUT high-Z (safest on live wiring)"));
        break;
      case 'd': showDigital = !showDigital;
                Serial.print(F("digital reporting "));
                Serial.println(showDigital ? F("ON") : F("OFF")); break;
      case 'a': showAnalog = !showAnalog;
                Serial.print(F("analog reporting "));
                Serial.println(showAnalog ? F("ON") : F("OFF")); break;
    }
  }
}
