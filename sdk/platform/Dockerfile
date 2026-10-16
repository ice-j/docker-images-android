# "base" is the tools image, wired up via docker-bake.hcl contexts.
FROM base

# Versions come from versions.env
ARG ANDROID_PLATFORM_VERSION
ARG ANDROID_PLATFORM_PACKAGES=android-${ANDROID_PLATFORM_VERSION}
ARG ANDROID_BUILD_TOOLS_VERSION

ENV ANDROID_PLATFORM_VERSION=${ANDROID_PLATFORM_VERSION} \
    ANDROID_BUILD_TOOLS_VERSION=${ANDROID_BUILD_TOOLS_VERSION}

RUN set -e \
    && packages="build-tools;$ANDROID_BUILD_TOOLS_VERSION" \
    && for p in $ANDROID_PLATFORM_PACKAGES; do packages="$packages platforms;$p"; done \
    && yes | sdkmanager $packages
