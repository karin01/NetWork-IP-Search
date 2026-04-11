package com.networkip.wifitool

import android.Manifest
import android.content.pm.PackageManager
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.net.wifi.WifiInfo
import android.net.wifi.WifiManager
import android.os.Build
import android.os.Bundle
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import com.networkip.wifitool.databinding.ActivityMainBinding

/**
 * 폰 단독 Wi‑Fi 정보 앱.
 * WHY: PC의 netsh/iperf와 달리 안드로이드는 WifiManager·NetworkCapabilities로만 동일 정보를 얻을 수 있습니다.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private lateinit var wifiManager: WifiManager

    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions(),
    ) {
        if (!hasWifiPermissions()) {
            Toast.makeText(
                this,
                "일부 권한이 거부되었습니다. SSID·스캔이 제한될 수 있습니다.",
                Toast.LENGTH_LONG,
            ).show()
        }
        refreshConnectionInfo()
        registerScanCallbackSafe()
    }

    private val scanCallback = object : WifiManager.ScanResultsCallback() {
        override fun onScanResultsAvailable() {
            runOnUiThread { displayScanResults() }
        }
    }

    private var scanCallbackRegistered = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)
        setSupportActionBar(binding.toolbar)

        wifiManager = applicationContext.getSystemService(WifiManager::class.java)
            ?: error("WifiManager를 가져올 수 없습니다.")

        binding.buttonRefresh.setOnClickListener {
            ensurePermissionsThen { refreshConnectionInfo() }
        }
        binding.buttonScan.setOnClickListener {
            ensurePermissionsThen { requestWifiScan() }
        }

        ensurePermissionsThen {
            refreshConnectionInfo()
            registerScanCallbackSafe()
        }
    }

    override fun onResume() {
        super.onResume()
        if (hasWifiPermissions()) {
            registerScanCallbackSafe()
        }
    }

    override fun onPause() {
        unregisterScanCallbackSafe()
        super.onPause()
    }

    /** 권한이 있으면 즉시 실행, 없으면 요청 후 콜백에서 갱신합니다. */
    private fun ensurePermissionsThen(block: () -> Unit) {
        if (hasWifiPermissions()) {
            block()
        } else {
            permissionLauncher.launch(requiredPermissionArray())
        }
    }

    private fun requiredPermissionArray(): Array<String> {
        val set = LinkedHashSet<String>()
        // SSID·스캔: 대부분 기기에서 정확 위치가 필요합니다.
        set.add(Manifest.permission.ACCESS_FINE_LOCATION)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            set.add(Manifest.permission.NEARBY_WIFI_DEVICES)
        }
        return set.toTypedArray()
    }

    private fun hasWifiPermissions(): Boolean =
        requiredPermissionArray().all { perm ->
            ContextCompat.checkSelfPermission(this, perm) == PackageManager.PERMISSION_GRANTED
        }

    private fun registerScanCallbackSafe() {
        if (scanCallbackRegistered || !hasWifiPermissions()) return
        try {
            // minSdk 29: Executor 오버로드만 사용 (구 Handler 오버로드는 최신 SDK 스텁과 충돌할 수 있음)
            wifiManager.registerScanResultsCallback(
                ContextCompat.getMainExecutor(this),
                scanCallback,
            )
            scanCallbackRegistered = true
        } catch (e: Exception) {
            Toast.makeText(
                this,
                "스캔 콜백 등록 실패: ${e.message ?: e.javaClass.simpleName}",
                Toast.LENGTH_SHORT,
            ).show()
        }
    }

    private fun unregisterScanCallbackSafe() {
        if (!scanCallbackRegistered) return
        try {
            wifiManager.unregisterScanResultsCallback(scanCallback)
        } catch (_: Exception) {
        }
        scanCallbackRegistered = false
    }

    private fun refreshConnectionInfo() {
        if (!wifiManager.isWifiEnabled) {
            binding.textConnection.text = getString(R.string.wifi_disabled)
            return
        }

        val sb = StringBuilder()

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            val cm = getSystemService(ConnectivityManager::class.java)
            val network = cm.activeNetwork
            if (network == null) {
                sb.appendLine("활성 네트워크 없음")
            } else {
                val caps = cm.getNetworkCapabilities(network)
                if (caps != null && caps.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)) {
                    when (val transportInfo = caps.transportInfo) {
                        is WifiInfo -> appendWifiInfo(sb, transportInfo)
                        else -> sb.appendLine("Wi‑Fi 세부 정보를 읽을 수 없습니다.")
                    }
                } else {
                    sb.appendLine("현재 Wi‑Fi에 연결되어 있지 않을 수 있습니다.")
                }
            }
        } else {
            @Suppress("DEPRECATION")
            appendWifiInfo(sb, wifiManager.connectionInfo)
        }

        binding.textConnection.text = sb.toString().trimEnd()
    }

    @Suppress("DEPRECATION")
    private fun appendWifiInfo(sb: StringBuilder, info: WifiInfo) {
        sb.appendLine("SSID: ${formatSsid(info.ssid)}")
        sb.appendLine("BSSID: ${info.bssid ?: "(알 수 없음)"}")
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            sb.appendLine("주파수: ${info.frequency} MHz")
        }
        sb.appendLine("RSSI: ${info.rssi} dBm")
        sb.appendLine("협상 링크: ${info.linkSpeed} Mbps")
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            sb.appendLine("표준: ${wifiStandardLabel(info.wifiStandard)}")
        }
    }

    /** AOSP WifiInfo 표준 상수와 동일한 정수 (플랫폼 상수명이 SDK 스텁에서 누락될 수 있어 리터럴 사용). */
    private fun wifiStandardLabel(code: Int): String = when (code) {
        0 -> "알 수 없음"
        1 -> "802.11a/b/g (legacy)"
        2 -> "802.11n"
        3 -> "802.11ac"
        4 -> "802.11ax"
        5 -> "802.11ad"
        6 -> "802.11be"
        else -> "코드 $code"
    }

    private fun formatSsid(raw: String?): String {
        if (raw.isNullOrBlank()) return "(알 수 없음)"
        var s = raw.trim()
        if (s.startsWith("\"") && s.endsWith("\"") && s.length >= 2) {
            s = s.substring(1, s.length - 1)
        }
        if (s.equals("<unknown ssid>", ignoreCase = true)) {
            return "(SSID 숨김 — 위치·정확 위치 권한 확인)"
        }
        return s
    }

    private fun requestWifiScan() {
        if (!wifiManager.isWifiEnabled) {
            Toast.makeText(this, R.string.wifi_disabled, Toast.LENGTH_LONG).show()
            return
        }
        @Suppress("DEPRECATION")
        val started = wifiManager.startScan()
        if (!started) {
            Toast.makeText(this, R.string.hint_throttle, Toast.LENGTH_LONG).show()
        } else {
            Toast.makeText(this, "스캔 요청함…", Toast.LENGTH_SHORT).show()
        }
        displayScanResults()
    }

    @Suppress("DEPRECATION")
    private fun displayScanResults() {
        if (!wifiManager.isWifiEnabled) {
            binding.textScanResults.text = getString(R.string.wifi_disabled)
            return
        }
        val results = wifiManager.scanResults ?: emptyList()
        if (results.isEmpty()) {
            binding.textScanResults.text = getString(R.string.scan_empty)
            return
        }
        val sorted = results.sortedByDescending { it.level }
        val lines = sorted.map { r ->
            val ssid = formatSsid(r.SSID)
            val cap = r.capabilities?.replace(",", " ") ?: ""
            "$ssid  |  ${r.level} dBm  |  ${r.frequency} MHz\n    $cap"
        }
        binding.textScanResults.text = lines.joinToString("\n\n")
    }
}
