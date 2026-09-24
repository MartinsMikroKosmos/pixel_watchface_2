import java.util.Properties

plugins {
    alias(libs.plugins.android.application)
}

// Upload key for Google Play, kept outside of git (see keystore.properties.example)
val keystoreProperties = Properties().apply {
    val file = rootProject.file("keystore.properties")
    if (file.exists()) file.inputStream().use { load(it) }
}

android {
    namespace = "de.martinsmikrokosmos.pergament"
    compileSdk {
        version = release(37)
    }

    defaultConfig {
        applicationId = "de.martinsmikrokosmos.pergament"
        minSdk = 34
        targetSdk = 37
        versionCode = 1
        versionName = "1.0"

    }

    signingConfigs {
        if (keystoreProperties.isNotEmpty()) {
            create("upload") {
                storeFile = file(keystoreProperties.getProperty("storeFile"))
                storePassword = keystoreProperties.getProperty("storePassword")
                keyAlias = keystoreProperties.getProperty("keyAlias")
                keyPassword = keystoreProperties.getProperty("keyPassword")
            }
        }
    }

    buildTypes {
        release {
            signingConfigs.findByName("upload")?.let { signingConfig = it }
            // R8 strips the generated R class: watch faces must not contain dex files
            optimization {
                enable = true
            }
        }
    }
    enableKotlin = false
}

dependencies {
}