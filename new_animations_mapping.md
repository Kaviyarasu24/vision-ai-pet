# Spritesheet Mappings & Reference Guide — `newimage.webp`

This document lists the visual previews and configuration parameters for all **22 rows** inside [`newimage.webp`](file:///d:/MCP/assets/robot/newimage.webp). 

---

## Mappings Table

| Row | Preview | Animation Name | Frame Count | Speed (ms) | Loop | Next State | Description / Trigger Case |
|:---:|:---:|---|:---:|:---:|:---:|:---:|---|
| **0** | ![Row 0](./assets/robot/temp_rows/row_0.png) | `idle` | 6 | 150 | True | -- | Standard blinking screen standby state. |
| **1** | ![Row 1](./assets/robot/temp_rows/row_1.png) | `running_right` | 8 | 100 | True | -- | Wandering towards the right. |
| **2** | ![Row 2](./assets/robot/temp_rows/row_2.png) | `running_left` | 8 | 100 | True | -- | Wandering towards the left. |
| **3** | ![Row 3](./assets/robot/temp_rows/row_3.png) | `wave` | 4 | 180 | False | `idle` | Greet or petting reaction wave. |
| **4** | ![Row 4](./assets/robot/temp_rows/row_4.png) | `jump` | 5 | 120 | False | `idle` | Hopping action or cursor drag reaction. |
| **5** | ![Row 5](./assets/robot/temp_rows/row_5.png) | `failed` | 8 | 150 | False | `idle` | Error or unsuccessful action reaction. |
| **6** | ![Row 6](./assets/robot/temp_rows/row_6.png) | `waiting` | 6 | 180 | True | -- | Idle, awaiting input or response pending. |
| **7** | ![Row 7](./assets/robot/temp_rows/row_7.png) | `running` | 6 | 100 | True | -- | General/alt movement loop. |
| **8** | ![Row 8](./assets/robot/temp_rows/row_8.png) | `review` | 6 | 200 | False | `idle` | Thinking/reviewing pose after an action. |
| **9** | ![Row 9](./assets/robot/temp_rows/row_9.png) | `charging` | 6 | 140 | True | `idle_charged` | Plugged in and actively drawing power. |
| **10** | ![Row 10](./assets/robot/temp_rows/row_10.png) | `charged_disconnected` | 5 | 200 | True | `idle` | Battery full, cable unplugged, content state. |
| **11** | ![Row 11](./assets/robot/temp_rows/row_11.png) | `charged_filled` | 6 | 130 | False | `charged_disconnected` | One-shot fill-up animation when charge completes. |
| **12** | ![Row 12](./assets/robot/temp_rows/row_12.png) | `need_charging` | 6 | 160 | True | `charging` | Low battery warning, prompts user to plug in. |
| **13** | ![Row 13](./assets/robot/temp_rows/row_13.png) | `wifi_connected` | 5 | 150 | False | `idle` | Signal-acquired confirmation after reconnect. |
| **14** | ![Row 14](./assets/robot/temp_rows/row_14.png) | `wifi_disconnected` | 5 | 180 | True | -- | Connection lost / offline state indicator. |
| **15** | ![Row 15](./assets/robot/temp_rows/row_15.png) | `muted` | 5 | 200 | True | -- | Sound turned off, persists until unmuted. |
| **16** | ![Row 16](./assets/robot/temp_rows/row_16.png) | `unmuted` | 5 | 150 | False | `idle` | Sound restored confirmation. |
| **17** | ![Row 17](./assets/robot/temp_rows/row_17.png) | `very_tired` | 6 | 220 | False | `need_rest` | Extended inactivity or low-energy state. |
| **18** | ![Row 18](./assets/robot/temp_rows/row_18.png) | `need_rest` | 6 | 220 | False | `sleeping` | Prompts user that pet wants to sleep soon. |
| **19** | ![Row 19](./assets/robot/temp_rows/row_19.png) | `sleeping` | 6 | 260 | True | -- | Idle-timeout or scheduled sleep state. |
| **20** | ![Row 20](./assets/robot/temp_rows/row_20.png) | `need_to_go_bed` | 5 | 200 | False | `sleeping` | Bedtime reminder before transitioning to sleep. |
| **21** | ![Row 21](./assets/robot/temp_rows/row_21.png) | `welcoming` | 6 | 130 | False | `idle` | App-open or user-return greeting. |
