# "base" is the platform image, wired up via docker-bake.hcl contexts.
FROM base

# Version comes from versions.env
ARG ANDROID_NDK_VERSION

ENV ANDROID_NDK_VERSION=${ANDROID_NDK_VERSION} \
    ANDROID_NDK_HOME=${ANDROID_HOME}/ndk/${ANDROID_NDK_VERSION}

RUN yes | sdkmanager "ndk;$ANDROID_NDK_VERSION"
