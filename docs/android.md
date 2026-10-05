# CV Analyser Android app

The Android APK bundles the React interface using Capacitor 8. It supports Android 7.0 (API 24) and newer. The Python/FastAPI analysis service runs on a computer or hosted server; it is not bundled into Android. A network connection is required for extraction, NLP, scoring and advice. The app includes an Android launcher icon, device file selection, native HTTP requests, server settings, and native PDF/JSON sharing.

## Install and connect

1. Transfer `output/android/cv-analyser-debug.apk` to your Android phone.
2. Open the file and allow installation from the app you used to open it if Android asks.
3. Open **CV Analyser** from your launcher.
4. In **Android server settings**, enter the analysis server address and server access token, test the connection and save. Saving restarts your current review. The token is kept in session storage; enter it again when starting a fresh app session.

The APK is debug-signed for local demonstrations. A Play Store release requires your own signing key and a hosted HTTPS backend. Release builds do not enable cleartext HTTP.

## Same-Wi-Fi demonstration

Start the backend from the repository root:

Set `CV_API_TOKEN` in the ignored root `.env` file to a random token of at least 32 characters. Generate one with `python -c "import secrets; print(secrets.token_urlsafe(32))"`. Copy that token into the app's server settings. This is a separate access token; never use your OpenAI API key for it. A token has been generated locally during the security review. The web interface also has server access settings when connecting to a protected backend.

```powershell
.\.venv\Scripts\python.exe scripts/run_backend.py --host 0.0.0.0 --port 8001
```

Connect the phone to the same Wi-Fi and enter `http://YOUR-COMPUTER-WIFI-IP:8001` in the app. Find that IPv4 address with `ipconfig`. Allow the backend through Windows Firewall on your private network when prompted. Keep the computer and API running. The phone must not use `localhost` or `127.0.0.1`, which refer to the phone itself. The APK does not need a Vite server or port 5173.

For the Android emulator use `http://10.0.2.2:8001`. For USB testing you can instead use `adb reverse tcp:8001 tcp:8001` and `http://127.0.0.1:8001`.

HTTP is enabled only by the debug manifest for controlled local demonstrations. Use fictional sample data on shared networks; use HTTPS for real candidate data. OpenAI configuration remains on the backend; never enter or bundle an OpenAI key into the APK.

## Build on Windows

Install Node.js 22+, Android SDK platform/build tools 36, and Java 21 (Android Studio includes a suitable JDK). Then run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_android.ps1
```

Pass `-AndroidSdk` and `-JavaHome` if your tools are installed elsewhere. The script installs locked dependencies, builds the frontend, synchronizes plugins/assets, compiles the debug APK and copies it to `output/android/cv-analyser-debug.apk`.

To edit the native project:

```powershell
cd frontend
npm run android:sync
npm run android:open
```

Re-run synchronization after changing frontend code. Build in Android Studio or with `android/gradlew.bat -p android assembleDebug`.

## File handling

The Android system file picker selects PDF/DOCX resumes; no broad storage permission is requested. Reports are written to app cache only on explicit export and shared with Android's file provider. Save the report using a chosen share destination; Android can reclaim cache files. Use **Clear cached reports** in server settings after sharing has finished to remove private export copies. The saved server address is stored on the device. Resume review state stays in memory and resets on restart. Application backup is disabled. Optional OpenAI requests still require explicit consent.

## Recorded verification

Version 0.11.0 compiled and APK signature verification passed. Android app lint reported zero errors (template/dependency warnings remain). All 20 frontend tests passed, including native binary preservation and cancellation/error cases. The installed APK was exercised on the Android 16 emulator against the local API: connection settings, sample PDF download, native multipart extraction, requirement review, 57.5% sample scoring, PDF/JSON cache exports, the Android share sheet and opening the system document picker. An Android binary-response issue was corrected by using an explicit arraybuffer request for downloads. The exported four-page PDF was opened and rendered, and JSON score contents were checked. npm audit reported no known vulnerabilities. Physical-phone and Play Store release testing remain separate steps.

## Reference documentation

- [Capacitor Android runtime](https://capacitorjs.com/docs/android)
- [Native HTTP and multipart fetch](https://capacitorjs.com/docs/apis/http)
- [Filesystem](https://capacitorjs.com/docs/apis/filesystem) and [Android sharing](https://capacitorjs.com/docs/apis/share)
