# ros2_plot

A small first pass at plotting ROS 2 bag data from a YAML config.

## Usage

Source ROS 2 first so `rosbag2_py`, `rclpy`, and message packages are importable:

```bash
source /opt/ros/<distro>/setup.bash
python3 ros2_plot.py examples/basic.yaml
```

Install non-ROS Python dependencies if needed:

```bash
python3 -m pip install -r requirements.txt
```

Common overrides:

```bash
python3 ros2_plot.py examples/basic.yaml --bag /data/run_42 --start 10 --end 25 --save run_42.png --no-show
```

## Config Shape

```yaml
bag: /path/to/rosbag
storage_id: sqlite3

time:
  mode: relative   # relative, bag, or unix
  start: 0.0
  end: 30.0

aliases:
  odom: /odom

styles:
  estimate:
    color: "#2563eb"
    linestyle: "-"
    linewidth: 2

plots:
  - title: Position
    y_label: position [m]
    series:
      - topic: odom
        field: pose.pose.position.x
        label: x
        style: estimate

output:
  save: plot.png
  show: true
  dpi: 140
```

Field paths use dot notation and simple indexes:

```yaml
field: pose.pose.position.x
field: ranges[42]
field: covariance[0]
```

Each series can also apply a simple linear transform:

```yaml
scale: 3.6
offset: 0.0
```

For multiple function steps, use `transforms` to apply value-based functions in order:

```yaml
- topic: /mavros/imu/data
  field: angular_velocity.z
  transforms:
    - name: abs
    - name: rad_to_deg
    - name: offset_value
      kwargs:
        amount: 2.0
```

Title and axis-label placement are configurable:

```yaml
- title: Body Rate X
  title_loc: left
  x_label: time [s]
  x_label_loc: right
  y_label: rad/s
  y_label_side: right
  y_label_loc: top
```

If you do not want a title or axis label, set it to `null` or `false`.

Supported placement values:

- `title_loc`: `left`, `center`, `right`
- `x_label_loc`: `left`, `center`, `right`
- `y_label_side`: `left`, `right`
- `y_label_loc`: `bottom`, `center`, `top`

Series can be either a direct numeric field or a derived function:

```yaml
- topic: imu
  function: quat_yaw
  label: yaw
```

Functions receive the topic message as their default input. If a function needs extra arguments, pass them through `kwargs`:

```yaml
- topic: /pose
  function: quat_yaw
  kwargs:
    field: pose.orientation
```

Built-in functions currently include:

- `quat_roll`
- `quat_pitch`
- `quat_yaw`
- `scale`
- `offset`
- `scale_value`
- `offset_value`
- `abs`
- `rad_to_deg`

Legend labels behave slightly differently:

- Omit `label` to get the default generated legend text.
- Set `label: null` or `label: false` to hide that series from the legend.

## Current Scope

This version intentionally handles scalar series only. A series can come from a numeric field directly or from a small built-in function fed by numeric fields from the same topic. It creates one vertical subplot for each entry in `plots`, with any number of series per subplot.

Good next requirements to explore:

- topic and field discovery commands
- CSV export of extracted data
- event-relative start times
- derived fields like quaternion yaw or vector norm
- multiple bags on the same plot
- config validation with clearer error locations
