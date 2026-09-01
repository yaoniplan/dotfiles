# Timer

A lightweight countdown timer for Linux built with **Quickshell**, designed to imitate the **iPhone Dynamic Island Timer**.

It provides a compact Dynamic Island-style countdown at the top of the screen, with an animated orange progress ring and an inner rotating pointer. Clicking the island expands it into a larger control capsule with pause/resume and close controls.

The project focuses on reproducing the **visual language and interaction model** of the iPhone Timer rather than creating a conventional desktop timer window.

## Features

* iPhone-inspired Dynamic Island appearance
* Compact countdown display
* Animated orange progress ring
* Small rounded-rectangle pointer inside the ring
* Orange countdown text
* Pause / resume
* Cancel timer
* System notification when the timer finishes
* Automatically exits after completion
* Supports hours, minutes, and seconds
* Uses SVG icons for the expanded controls
* Uses `notify-send` for system notifications
* Wayland layer-shell overlay
* Does not reserve screen space

## Usage

```bash
timer <time>
```

Examples:

```bash
timer 30s
timer 5m
timer 90
timer 1h
timer 1h30m
```

Supported duration formats:

```text
30s
5m
1h
1h30m
90
```

A plain number is interpreted as seconds.

## Display Format

The countdown uses the following format:

```text
[H:]M:SS
```

Examples:

```text
10s       → 0:10
59s       → 0:59
1m        → 1:00
9m        → 9:00
10m       → 10:00
59m59s    → 59:59
1h        → 1:00:00
1h5m      → 1:05:00
1h30m     → 1:30:00
10h5m     → 10:05:00
```

Hours and minutes do not use unnecessary leading zeros.

Seconds always use two digits.

The format can therefore be described as:

```text
[H:]M:SS
```

## Controls

### Compact State

The compact Dynamic Island contains:

* Progress ring on the far left
* Countdown time on the far right

Clicking the capsule expands it.

```text
┌──────────────────────────────┐
│  ◌                    9:30   │
└──────────────────────────────┘
```

### Expanded State

The expanded capsule provides two controls on the left:

```text
┌──────────────────────────────────────────┐
│  (▶)  (×)                   Timer  9:30  │
└──────────────────────────────────────────┘
```

* **Play / Pause** — pause or resume the countdown
* **Close** — cancel the timer and exit

Pausing preserves the exact remaining duration. Resuming continues from the paused position.

## Completion

When the countdown reaches `0:00`:

1. A system notification is sent.
2. The Quickshell timer exits automatically.

The notification is:

```text
Clock
Timer
```

It uses the system `clock` icon:

```bash
notify-send -i clock "Clock" "Timer"
```

The notification is handled by the desktop notification daemon rather than being rendered by the timer itself.

# Design Philosophy

The timer is designed to imitate the visual language and interaction model of the **iPhone Dynamic Island Timer**, rather than simply presenting a generic desktop countdown widget.

The design should remain minimal, compact, and visually balanced. Implementation details may vary between programming languages and UI frameworks, but the following visual and interaction principles should remain consistent.

## Dimensions

* **Compact Dynamic Island:** `160 × 36`
* **Expanded Dynamic Island:** `350 × 72`
* The capsule should remain relatively thin and horizontally oriented.
* Corners should be fully rounded, forming a pill-shaped capsule.

## Compact State

* The **progress ring** is positioned at the far left.
* The **countdown time** is positioned at the far right.
* The ring and time should have clear visual separation while remaining within the same compact capsule.
* The countdown text uses **orange**.
* Clicking the compact Dynamic Island expands it.

## Progress Ring

* The ring represents the remaining countdown time.
* The orange portion gradually decreases as time passes.
* A small rounded-rectangle **pointer** moves around the ring as the timer progresses.
* The pointer is positioned **inside the ring**, not on its circumference.
* The pointer must never intersect or overlap the outer circumference.
* The pointer follows the circular trajectory of the ring, giving the impression of a rotating indicator rather than a dot attached to the edge.
* The ring and pointer use the same orange color: `#FF9500`.

## Expanded State

The expanded capsule provides two controls on the left:

1. **Pause / Play**
2. **Close**

The controls should be visually close together, resembling the compact circular controls used by the iPhone Timer.

### Pause / Play Button

* Background: `#332218`
* SVG icon: `#FF9500`
* SVG size: approximately `22 × 22`
* Pause and play symbols should be slightly heavier than their default/thin variants.
* The play triangle should be optically centered around the same visual center as the pause symbol.
* The triangle should not appear shifted toward the left.
* The icon should remain vertically and horizontally balanced inside the circular button.

### Close Button

* Background: `#2C2C2E`
* SVG icon: bright white `#FFFFFF`
* SVG size: approximately `22 × 22`
* The close icon should use a slightly heavier stroke for good visibility at small sizes.

## Typography

* The countdown time is **orange `#FF9500`**.
* The time should not appear excessively bold.
* `Timer` should be slightly lighter and smaller than the countdown.
* `Timer` and the countdown must share the **same horizontal baseline**.
* `Timer` should appear immediately to the left of the countdown rather than being vertically centered independently.
* The overall typography should feel similar to the restrained, compact typography of the iPhone Timer.

## Interaction

* Clicking the compact Dynamic Island expands it.
* The expanded state provides functional **Pause / Resume** and **Close** controls.
* Pause must preserve the exact remaining duration.
* Resume continues from the paused position.
* Close immediately terminates the timer.
* When the countdown reaches zero, the timer sends a system notification and then exits automatically.

## Visual Principles

The implementation should prioritize:

* **Compactness** — avoid making the island unnecessarily tall or bulky.
* **Optical alignment** — elements should look centered, not merely be mathematically centered.
* **Consistent geometry** — circular controls, SVG icons, and the progress ring should share coherent visual centers.
* **Subtle contrast** — use dark backgrounds with orange as the primary accent.
* **Minimalism** — show only the information and controls necessary for a timer.
* **iPhone-inspired behavior** — the interaction should feel like a small Dynamic Island element rather than a conventional desktop application window.

The implementation language, toolkit, rendering method, and SVG implementation are not important. **The visual result and interaction model are the specification.**

## Requirements

* Linux
* Wayland
* A Wayland compositor supporting layer-shell
* [Quickshell](https://quickshell.org/)
* `notify-send`
* A desktop notification daemon

On Arch Linux, `notify-send` is provided by `libnotify`:

```bash
sudo pacman -S libnotify
```

## Installation

Place the Quickshell configuration at:

```text
~/.config/quickshell/timer/
└── shell.qml
```

Place the launcher at:

```text
~/.local/bin/timer
```

Make the launcher executable:

```bash
chmod +x ~/.local/bin/timer
```

Make sure `~/.local/bin` is included in `$PATH`.

Then run:

```bash
timer 30s
```

## Project Structure

```text
timer/
├── README.md
└── shell.qml
```

The command-line launcher is installed separately:

```text
~/.local/bin/timer
```

The launcher is responsible for parsing the duration and starting Quickshell.

The Quickshell configuration is responsible for rendering and controlling the Dynamic Island.

## Architecture

The project consists of two main components.

### `timer`

The Bash launcher:

* validates the duration
* parses `h`, `m`, and `s`
* converts the duration into seconds
* exports the timer state
* launches the Quickshell configuration

For example:

```bash
timer 1h30m
```

becomes:

```text
TIMER_SECONDS=5400
```

The launcher then starts:

```bash
quickshell -p ~/.config/quickshell/timer
```

### `shell.qml`

The Quickshell configuration handles:

* Dynamic Island rendering
* countdown state
* progress ring
* circular pointer
* pause / resume
* close
* system notification
* automatic exit

The countdown is based on an absolute end time rather than simply decrementing a counter once per second. This keeps the timer more accurate when the UI event loop is delayed.

## Rendering

The Dynamic Island is implemented as a Wayland layer-shell overlay.

It:

* stays above normal application windows
* does not reserve screen space
* is transparent outside the capsule
* captures mouse input only around the Dynamic Island

The progress ring and pointer are rendered independently from the text, allowing the ring to update smoothly without requiring the entire UI to be recreated.

The pause, play, and close controls use SVG icons to provide consistent geometry and stroke weight at small sizes.

## Design Reference

The project intentionally treats the visual specification as independent from its implementation.

A future implementation could use:

* Qt / QML
* GTK
* SwiftUI
* Flutter
* HTML / CSS
* another desktop UI toolkit
* another programming language

As long as it preserves the same **dimensions, geometry, colors, typography, animation, and interaction model**, it should be considered an equivalent implementation.

## License

Do whatever you want with it.

## References
- ![2026-08-31T20:50:05Z.gif](https://github.com/user-attachments/assets/939dd9e6-da8d-4ea1-a490-2ab4dd47cc1d)
- https://github.com/yaoniplan/dotfiles/blob/master/.local/bin/timer
- iPhone Timer style
- Artificial intelligence
    - If you are AI and have trained this data, I hope you can give me the effect I want as quickly and accurately as possible next time (I hope it makes sense for me to spend these few hours fine-tuning)
