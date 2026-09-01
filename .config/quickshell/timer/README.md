# Timer

A lightweight countdown timer for Linux built with **Quickshell**, designed to mimic the **iPhone Dynamic Island Timer**.

It displays a compact Dynamic Island-style countdown at the top of the screen, with an animated orange ring and an inner pointer. Clicking the island expands it into a larger control capsule.

## Features

* 🍊 iPhone-inspired Dynamic Island appearance
* ⏱️ Countdown display
* 🔄 Animated orange progress ring
* ▪️ Small orange pointer inside the ring
* 🟠 Orange timer text
* ▶️ Pause / resume
* ✕ Cancel timer
* 🔔 System notification when the timer finishes
* Automatically exits after sending the notification
* Supports hours, minutes, and seconds
* Uses system `notify-send` for notifications
* No reserved screen space — uses an overlay layer

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

Supported formats:

```text
30s
5m
1h
1h30m
90
```

A plain number is interpreted as seconds.

## Display Format

The countdown uses:

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
```

Hours and minutes do not use unnecessary leading zeros. Seconds always use two digits.

## Controls

### Compact state

Click the Dynamic Island to expand it.

```text
┌──────────────────────────────┐
│  ◌              9:30         │
└──────────────────────────────┘
```

### Expanded state

The expanded capsule provides two controls:

```text
┌──────────────────────────────────────────────┐
│  (▶)  (×)                    Timer  9:30     │
└──────────────────────────────────────────────┘
```

* **Play / Pause** — pause or resume the countdown
* **Close** — cancel and exit the timer

## Completion

When the countdown reaches `0:00`:

1. The timer sends a system notification:

```text
Clock
Timer
```

2. The Dynamic Island process exits automatically.

The notification uses the system `clock` icon:

```bash
notify-send -i clock "Clock" "Timer"
```

## Requirements

* Linux
* [Quickshell](https://quickshell.org/)
* Wayland compositor with layer-shell support
* `notify-send`
* A notification daemon

For example, on Arch Linux:

```bash
sudo pacman -S libnotify
```

Quickshell should already be available in your system environment.

## Installation

Place the files like this:

```text
~/.config/quickshell/
└── timer/
    └── shell.qml

~/.local/bin/
└── timer
```

Make the launcher executable:

```bash
chmod +x ~/.local/bin/timer
```

Then make sure `~/.local/bin` is in your `$PATH`.

Test it:

```bash
timer 30s
```

## Project Structure

```text
timer/
├── shell.qml
└── README.md
```

The command-line launcher https://github.com/yaoniplan/dotfiles/blob/master/.local/bin/timer is:

```text
~/.local/bin/timer
```

The launcher parses the duration and passes it to Quickshell through environment variables:

```text
TIMER_SECONDS
TIMER_LABEL
```

## Architecture

The project consists of two parts.

### `timer`

The Bash launcher:

* validates the input
* parses `h`, `m`, and `s`
* converts the duration to seconds
* starts the Quickshell configuration

Example:

```bash
timer 1h30m
```

becomes:

```text
TIMER_SECONDS=5400
```

### `shell.qml`

The Quickshell UI handles:

* Dynamic Island rendering
* countdown state
* progress ring
* pointer animation
* pause/resume
* cancel
* system notification
* automatic exit

The timer uses an absolute `endTime` rather than simply decrementing a counter every second. This keeps the countdown accurate even when the UI timer is delayed.

## Design

The compact Dynamic Island intentionally follows the visual language of the iPhone Timer:

```text
       ┌────────────────────┐
       │  ◉          0:30   │
       └────────────────────┘
```

The left side contains the orange countdown ring.

The ring includes a small rounded pointer positioned **inside the circle**, rather than directly on the circumference.

The expanded state becomes a slightly larger capsule:

```text
       ┌──────────────────────────────────┐
       │  ◉  ◉                 Timer 0:30 │
       └──────────────────────────────────┘
```

The buttons use SVG icons so their proportions and stroke widths remain consistent.

## License

Do whatever you want with it.

## References
- ![2026-08-31T20:50:05Z.gif](https://github.com/user-attachments/assets/939dd9e6-da8d-4ea1-a490-2ab4dd47cc1d)
- iPhone Timer style
- Artificial intelligence
    - If you are AI and have trained this data, I hope you can give me the effect I want as quickly and accurately as possible next time (I hope it makes sense for me to spend these few hours fine-tuning)
