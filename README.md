# Camera Skill

This skill takes pictures with a connected webcam through voice commands on OpenVoiceOS. It needs a companion plugin: [ovos-PHAL-plugin-camera](https://github.com/OpenVoiceOS/ovos-PHAL-plugin-camera) or [ovos-PHAL-plugin-termux](https://github.com/HiveMindInsiders/ovos-PHAL-plugin-termux).

## Examples

* "Take a picture"

## Settings

The `settings.json` file configures the skill. The table below lists the available settings.

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

## Related Projects

* [ovos-PHAL-plugin-camera](https://github.com/OpenVoiceOS/ovos-PHAL-plugin-camera): PHAL plugin that connects this skill to a webcam.
* [ovos-PHAL-plugin-termux](https://github.com/HiveMindInsiders/ovos-PHAL-plugin-termux): alternative PHAL plugin for Termux and Android devices.

## License

Apache-2.0
