import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import QtQuick

ShellRoot {
    id: root

    // ---------------------------------------------------------
    // Constants
    // ---------------------------------------------------------

    readonly property color accent: "#FF9500"
    readonly property color bgRing: "#3A3A3C"

    readonly property string playSvg:
        "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath d='M7 4.5C6.3 4.1 5.4 4.6 5.4 5.45V18.55C5.4 19.4 6.3 19.9 7 19.5L19.2 12.95C19.95 12.55 19.95 11.45 19.2 11.05L7 4.5Z' fill='%23FF9500'/%3E%3C/svg%3E"

    readonly property string pauseSvg:
        "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Crect x='5' y='4' width='5' height='16' rx='2' fill='%23FF9500'/%3E%3Crect x='14' y='4' width='5' height='16' rx='2' fill='%23FF9500'/%3E%3C/svg%3E"

    readonly property string closeSvg:
        "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath d='M5.2 5.2L18.8 18.8M18.8 5.2L5.2 18.8' stroke='%23FFFFFF' stroke-width='2.6' stroke-linecap='round'/%3E%3C/svg%3E"

    // ---------------------------------------------------------
    // State
    // ---------------------------------------------------------

    property int duration: 0
    property int remaining: 0
    property string label: ""
    property bool done: false
    property bool expanded: false
    property bool paused: false

    property double endTime: 0
    property double pausedMilliseconds: 0

    property double millisecondsLeft: Math.max(0, endTime - Date.now())
    property real progress: duration > 0
        ? Math.max(0, Math.min(1, millisecondsLeft / (duration * 1000)))
        : 0


    // ============================================================
    // PANEL
    // ============================================================

    PanelWindow {
        id: panel

        anchors {
            top: true
            bottom: true
            left: true
            right: true
        }

        color: "transparent"
        exclusionMode: ExclusionMode.Ignore
        WlrLayershell.layer: WlrLayer.Overlay

        mask: Region { item: island }


        // ========================================================
        // DYNAMIC ISLAND
        // ========================================================

        Item {
            id: island

            width: root.expanded ? 350 : 160
            height: root.expanded ? 72 : 36

            anchors {
                top: parent.top
                horizontalCenter: parent.horizontalCenter
                topMargin: 8
            }

            Behavior on width { NumberAnimation { duration: 320; easing.type: Easing.OutCubic } }
            Behavior on height { NumberAnimation { duration: 320; easing.type: Easing.OutCubic } }


            // ----------------------------------------------------
            // Shadow
            // ----------------------------------------------------

            Rectangle {
                anchors.fill: parent
                anchors.topMargin: 2
                radius: height / 2
                color: "#80000000"
                opacity: 0.6
            }


            // ----------------------------------------------------
            // Background
            // ----------------------------------------------------

            Rectangle {
                id: background

                anchors.fill: parent
                radius: height / 2
                color: "#000000"
                border.width: 1
                border.color: "#18181A"


                // =================================================
                // COMPACT STATE
                // =================================================

                Item {
                    id: compactContent

                    anchors.fill: parent

                    opacity: root.expanded ? 0 : 1
                    visible: opacity > 0

                    Behavior on opacity { NumberAnimation { duration: 100 } }


                    // --------------------------------------------
                    // RING
                    // --------------------------------------------

                    Canvas {
                        id: compactRing

                        width: 27
                        height: 27

                        anchors {
                            left: parent.left
                            leftMargin: 8
                            verticalCenter: parent.verticalCenter
                        }

                        property real progress: root.progress

                        onPaint: {
                            var ctx = getContext("2d")
                            ctx.reset()

                            var cx = width / 2
                            var cy = height / 2
                            var radius = 9.5
                            var startAngle = -Math.PI / 2
                            var endAngle = startAngle + progress * 2 * Math.PI

                            // Background ring
                            ctx.beginPath()
                            ctx.arc(cx, cy, radius, 0, 2 * Math.PI)
                            ctx.lineWidth = 3
                            ctx.lineCap = "round"
                            ctx.strokeStyle = root.bgRing
                            ctx.stroke()

                            if (progress > 0) {
                                // Orange arc
                                ctx.beginPath()
                                ctx.arc(cx, cy, radius, startAngle, endAngle, false)
                                ctx.lineWidth = 3
                                ctx.lineCap = "round"
                                ctx.strokeStyle = root.accent
                                ctx.stroke()

                                // Pointer
                                var pr = radius - 5.5
                                var px = cx + pr * Math.cos(endAngle)
                                var py = cy + pr * Math.sin(endAngle)

                                ctx.save()
                                ctx.translate(px, py)
                                ctx.rotate(endAngle)

                                ctx.beginPath()
                                ctx.roundedRect(-2.5, -1.75, 5, 3.5, 1.75, 1.75)
                                ctx.fillStyle = root.accent
                                ctx.fill()

                                ctx.restore()
                            }
                        }

                        Connections {
                            target: root

                            function onProgressChanged() { compactRing.requestPaint() }
                            function onMillisecondsLeftChanged() { compactRing.requestPaint() }
                        }

                        Component.onCompleted: requestPaint()
                    }


                    // --------------------------------------------
                    // COMPACT TIME
                    // --------------------------------------------

                    Text {
                        id: compactTime

                        anchors {
                            right: parent.right
                            rightMargin: 10
                            verticalCenter: parent.verticalCenter
                        }

                        text: root.done ? "0:00" : formatTime(root.remaining)
                        color: root.accent

                        font.family: "Sans"
                        font.pixelSize: 16
                        font.weight: Font.DemiBold

                        horizontalAlignment: Text.AlignRight
                    }
                }


                // =================================================
                // EXPANDED STATE
                // =================================================

                Item {
                    id: expandedContent

                    anchors.fill: parent

                    opacity: root.expanded ? 1 : 0
                    visible: opacity > 0

                    Behavior on opacity { NumberAnimation { duration: 160 } }


                    // --------------------------------------------
                    // PAUSE / PLAY BUTTON
                    // --------------------------------------------

                    Rectangle {
                        id: pauseButton

                        width: 44
                        height: 44

                        anchors {
                            left: parent.left
                            leftMargin: 14
                            verticalCenter: parent.verticalCenter
                        }

                        radius: 22
                        color: "#332218"

                        Image {
                            anchors.centerIn: parent
                            width: 27
                            height: 27
                            fillMode: Image.PreserveAspectFit
                            source: root.paused ? root.playSvg : root.pauseSvg
                            smooth: true
                        }

                        MouseArea {
                            anchors.fill: parent
                            onClicked: togglePause()
                        }
                    }


                    // --------------------------------------------
                    // CLOSE BUTTON
                    // --------------------------------------------

                    Rectangle {
                        id: closeButton

                        width: 44
                        height: 44

                        anchors {
                            left: pauseButton.right
                            leftMargin: 6
                            verticalCenter: parent.verticalCenter
                        }

                        radius: 22
                        color: "#2C2C2E"

                        Image {
                            anchors.centerIn: parent
                            width: 27
                            height: 27
                            fillMode: Image.PreserveAspectFit
                            source: root.closeSvg
                            smooth: true
                        }

                        MouseArea {
                            anchors.fill: parent
                            onClicked: Qt.quit()
                        }
                    }


                    // --------------------------------------------
                    // TIME
                    // --------------------------------------------

                    Text {
                        id: countdown

                        anchors {
                            right: parent.right
                            rightMargin: 22
                            verticalCenter: parent.verticalCenter
                        }

                        text: root.done ? "0:00" : formatTime(root.remaining)
                        color: root.accent

                        font.family: "Sans"
                        font.pixelSize: 32
                        font.weight: Font.Medium

                        horizontalAlignment: Text.AlignRight
                    }


                    // --------------------------------------------
                    // LABEL
                    // --------------------------------------------

                    Text {
                        id: timerLabel

                        anchors {
                            right: countdown.left
                            rightMargin: 6
                            baseline: countdown.baseline
                        }

                        text: "Timer"
                        color: root.accent

                        font.family: "Sans"
                        font.pixelSize: 13
                        font.weight: Font.DemiBold

                        horizontalAlignment: Text.AlignRight
                    }


                    // --------------------------------------------
                    // CLICK OUTSIDE BUTTONS
                    // --------------------------------------------

                    MouseArea {
                        anchors.fill: parent
                        z: -1
                        onClicked: root.expanded = false
                    }
                }


                // =================================================
                // COMPACT CLICK AREA
                // =================================================

                MouseArea {
                    anchors.fill: parent
                    visible: !root.expanded
                    onClicked: root.expanded = true
                }
            }
        }
    }


    // ============================================================
    // FORMAT TIME
    // ============================================================

    // [H:]M:SS
    function formatTime(sec) {
        sec = Math.max(0, sec)

        var h = Math.floor(sec / 3600)
        var m = Math.floor((sec % 3600) / 60)
        var s = sec % 60

        var mm = (m < 10 ? "0" : "") + m
        var ss = (s < 10 ? "0" : "") + s

        return h > 0 ? (h + ":" + mm + ":" + ss) : (m + ":" + ss)
    }


    // ============================================================
    // HELPERS
    // ============================================================

    function remainingMs() {
        return Math.max(0, root.endTime - Date.now())
    }


    // ============================================================
    // PAUSE / RESUME
    // ============================================================

    function togglePause() {
        if (root.done)
            return

        if (root.paused) {
            // Resume
            root.endTime = Date.now() + root.pausedMilliseconds
            root.millisecondsLeft = root.pausedMilliseconds
            root.paused = false
            tickTimer.start()
        } else {
            // Pause
            root.pausedMilliseconds = remainingMs()
            root.millisecondsLeft = root.pausedMilliseconds
            root.remaining = Math.ceil(root.pausedMilliseconds / 1000)
            root.paused = true
            tickTimer.stop()
        }
    }


    // ============================================================
    // COUNTDOWN
    // ============================================================

    Timer {
        id: tickTimer

        interval: 50
        repeat: true
        running: false

        onTriggered: {
            if (root.paused)
                return

            var left = remainingMs()

            root.millisecondsLeft = left
            root.remaining = Math.ceil(left / 1000)

            if (left <= 0) {
                stop()
                root.millisecondsLeft = 0
                root.remaining = 0
                root.done = true

                // Play alarm sound once and send notification.
                alarmProc.running = true
                notificationProc.running = true

                return
            }

            compactRing.requestPaint()
        }
    }


    // ============================================================
    // ALARM LOOP
    // ============================================================

    Timer {
        id: alarmLoop

        interval: 2000
        repeat: true
        running: false

        onTriggered: {
            alarmProc.running = false
            alarmProc.running = true
        }
    }

    function stopAlarm() {
        alarmLoop.stop()
        alarmProc.running = false
    }


    // ============================================================
    // ALARM SOUND
    // ============================================================

    Process {
        id: alarmProc

        running: false

        command: ["paplay", "/usr/share/sounds/freedesktop/stereo/alarm-clock-elapsed.oga"]

        onExited: Qt.quit()
    }


    // ============================================================
    // SYSTEM NOTIFICATION
    // ============================================================

    Process {
        id: notificationProc

        running: false

        command: ["notify-send", "-i", "clock", "Clock", "Timer"]
    }


    // ============================================================
    // READ ENVIRONMENT
    // ============================================================

    Process {
        id: envProc

        running: true

        command: ["sh", "-c",
            "printf '%s\\n%s\\n' \"$TIMER_SECONDS\" \"${TIMER_LABEL:-}\""
        ]

        stdout: StdioCollector {
            onStreamFinished: {
                var lines = this.text.trim().split("\n")
                var d = parseInt(lines[0] || "0", 10)

                root.duration = d
                root.label = lines.length > 1 ? lines[1] : ""

                if (d > 0) {
                    root.remaining = d
                    root.endTime = Date.now() + d * 1000
                    root.millisecondsLeft = d * 1000
                    root.done = false
                    root.paused = false
                    root.expanded = false

                    compactRing.requestPaint()
                    tickTimer.start()
                } else {
                    Qt.quit()
                }
            }
        }
    }
}
