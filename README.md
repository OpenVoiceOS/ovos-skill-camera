# Camera Skill

Camera skill for OpenVoiceOS, needs the companion plugin [ovos-PHAL-plugin-camera](https://github.com/OpenVoiceOS/ovos-PHAL-plugin-camera) or [ovos-PHAL-plugin-termux](https://github.com/HiveMindInsiders/ovos-PHAL-plugin-termux)

## Description

This skill allows you to ask to take pictures using a connected webcam. You can configure various settings to customize its behavior.

## Examples

* "Take a picture"

## Settings

The `settings.json` file allows you to configure the behavior of the Camera Skill. Below are the available settings:

| Setting Name         | Type     | Default       | Description                                                                 |
|----------------------|----------|---------------|-----------------------------------------------------------------------------|
| `play_sound`         | Boolean  | `true`        | Whether to play a sound when a picture is taken.                           |
| `camera_sound_path`  | String   | `camera.wav`  | Path to the sound file to play when taking a picture.                      |
| `pictures_folder`    | String   | `~/Pictures`  | Directory where pictures are saved.                                        |

### Example `settings.json`

```json
{
  "play_sound": true,
  "camera_sound_path": "/path/to/camera.wav",
  "pictures_folder": "/home/user/Pictures"
}
```


