# Docker images with Android SDK

[![Build](https://github.com/ice-j/docker-images-android/actions/workflows/build.yml/badge.svg)](https://github.com/ice-j/docker-images-android/actions/workflows/build.yml)
[![Update versions](https://github.com/ice-j/docker-images-android/actions/workflows/update.yml/badge.svg)](https://github.com/ice-j/docker-images-android/actions/workflows/update.yml)

Images are updated automatically when Google publishes a new stable Android
SDK command-line tools, platform, build-tools or NDK release.

```console
docker run --rm -it \
  --volume "$PWD:/build" \
  --workdir /build \
  ghcr.io/ice-j/android-sdk:latest \
  ./gradlew :app:assembleDebug
```

The example above mounts current working directory and runs a Gradle build.

## Tags

| Tag                                    | Contents                                         |
| -------------------------------------- | ------------------------------------------------ |
| `tools`, `tools-<build>`               | JDK, command-line tools, platform-tools, emulator |
| `latest`, `<api>`                      | `tools` + newest platform and build-tools        |
| `<api>-build-tools-<version>`          | same, pinned to a build-tools version            |
| `latest-ndk`, `<api>-ndk`              | `<api>` + newest NDK                             |
| `<api>-ndk-<version>`                  | same, pinned to an NDK version                   |

`<api>` is the platform API level (e.g. `37`). Its image contains the base
platform (e.g. `platforms;android-37.0`) and the newest minor SDK release
(e.g. `platforms;android-37.2`). The current versions are in
[`versions.env`](versions.env).

All images are built for `linux/amd64` and `linux/arm64` (the emulator and
the NDK toolchains are only usable on amd64).

## How updates work

- [`versions.env`](versions.env) is the single source of truth for versions.
- [`scripts/update-versions.py`](scripts/update-versions.py) reads Google's SDK
  repository manifest (the one `sdkmanager` uses) and bumps `versions.env` to
  the newest stable releases. Versions only move forward.
- [`update.yml`](.github/workflows/update.yml) runs it daily. When something
  changed, it commits the bump to `auto/update-versions`, builds and
  smoke-tests the images from that branch, pushes them, and then
  fast-forwards `main`. If anything fails, it opens an issue labelled
  `auto-update` and leaves `main` alone.
- [`build.yml`](.github/workflows/build.yml) builds pull requests (without
  pushing) and pushes on changes to `main`.

To stay on an NDK LTS line instead of the newest NDK, set e.g.
`ANDROID_NDK_MAJOR=27` in `versions.env`.

## Building locally

```console
python3 scripts/update-versions.py --dry-run    # see what's new
set -a; . ./versions.env; set +a
docker buildx bake                              # tools, platform and ndk
docker buildx bake --load --set '*.platform=linux/amd64' platform
```

## GitHub Container Registry

https://github.com/ice-j/docker-images-android/pkgs/container/android-sdk
