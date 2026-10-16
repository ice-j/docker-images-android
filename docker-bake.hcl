# Build all images locally:
#   set -a; . ./versions.env; set +a; docker buildx bake
# The variables below are read from the environment (versions.env in CI).

variable "REGISTRY" {
  default = "ghcr.io/ice-j"
}

variable "IMAGE_NAME" {
  default = "android-sdk"
}

variable "SOURCE_URL" {
  default = "https://github.com/ice-j/docker-images-android"
}

# Set to "gha" in GitHub Actions to use the Actions cache.
variable "CACHE_TYPE" {
  default = ""
}

variable "ANDROID_SDK_TOOLS_VERSION" {}
variable "ANDROID_PLATFORM_VERSION" {}
variable "ANDROID_PLATFORM_PACKAGES" {}
variable "ANDROID_BUILD_TOOLS_VERSION" {}
variable "ANDROID_NDK_VERSION" {}

function "tag" {
  params = [suffix]
  result = "${REGISTRY}/${IMAGE_NAME}:${suffix}"
}

function "cache_from" {
  params = [scope]
  result = CACHE_TYPE == "" ? [] : ["type=${CACHE_TYPE},scope=${scope}"]
}

function "cache_to" {
  params = [scope]
  result = CACHE_TYPE == "" ? [] : ["type=${CACHE_TYPE},scope=${scope},mode=max"]
}

group "default" {
  targets = ["tools", "platform", "ndk"]
}

target "_common" {
  platforms = ["linux/amd64", "linux/arm64"]
  labels = {
    "org.opencontainers.image.source" = SOURCE_URL
  }
}

target "tools" {
  inherits   = ["_common"]
  context    = "sdk/tools"
  cache-from = cache_from("tools")
  cache-to   = cache_to("tools")
  args = {
    ANDROID_SDK_TOOLS_VERSION = ANDROID_SDK_TOOLS_VERSION
  }
  tags = [
    tag("tools"),
    tag("tools-${ANDROID_SDK_TOOLS_VERSION}"),
  ]
}

target "platform" {
  inherits   = ["_common"]
  context    = "sdk/platform"
  contexts   = { base = "target:tools" }
  cache-from = cache_from("platform")
  cache-to   = cache_to("platform")
  args = {
    ANDROID_PLATFORM_VERSION    = ANDROID_PLATFORM_VERSION
    ANDROID_PLATFORM_PACKAGES   = ANDROID_PLATFORM_PACKAGES
    ANDROID_BUILD_TOOLS_VERSION = ANDROID_BUILD_TOOLS_VERSION
  }
  tags = [
    tag("latest"),
    tag("${ANDROID_PLATFORM_VERSION}"),
    tag("${ANDROID_PLATFORM_VERSION}-build-tools-${ANDROID_BUILD_TOOLS_VERSION}"),
  ]
}

target "ndk" {
  inherits   = ["_common"]
  context    = "sdk/ndk"
  contexts   = { base = "target:platform" }
  cache-from = cache_from("ndk")
  cache-to   = cache_to("ndk")
  args = {
    ANDROID_NDK_VERSION = ANDROID_NDK_VERSION
  }
  tags = [
    tag("latest-ndk"),
    tag("${ANDROID_PLATFORM_VERSION}-ndk"),
    tag("${ANDROID_PLATFORM_VERSION}-ndk-${ANDROID_NDK_VERSION}"),
  ]
}
