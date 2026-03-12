param(
    [string]$OutputDir = "certs",
    [int]$DaysValid = 365,
    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$outputPath = Join-Path (Get-Location) $OutputDir
$certPath = Join-Path $outputPath "localhost.pem"
$keyPath = Join-Path $outputPath "localhost-key.pem"

if (((Test-Path $certPath) -or (Test-Path $keyPath)) -and -not $Force) {
    throw "TLS files already exist in '$outputPath'. Re-run with -Force to overwrite them."
}

New-Item -ItemType Directory -Path $outputPath -Force | Out-Null

$rsa = [System.Security.Cryptography.RSA]::Create(2048)
try {
    $subject = [System.Security.Cryptography.X509Certificates.X500DistinguishedName]::new("CN=localhost")
    $request = [System.Security.Cryptography.X509Certificates.CertificateRequest]::new(
        $subject,
        $rsa,
        [System.Security.Cryptography.HashAlgorithmName]::SHA256,
        [System.Security.Cryptography.RSASignaturePadding]::Pkcs1
    )

    $sanBuilder = [System.Security.Cryptography.X509Certificates.SubjectAlternativeNameBuilder]::new()
    $sanBuilder.AddDnsName("localhost")
    $sanBuilder.AddIpAddress([System.Net.IPAddress]::Parse("127.0.0.1"))
    $sanBuilder.AddIpAddress([System.Net.IPAddress]::Parse("::1"))
    $request.CertificateExtensions.Add($sanBuilder.Build())
    $request.CertificateExtensions.Add([System.Security.Cryptography.X509Certificates.X509BasicConstraintsExtension]::new($false, $false, 0, $false))
    $keyUsage = [System.Security.Cryptography.X509Certificates.X509KeyUsageFlags]::DigitalSignature -bor [System.Security.Cryptography.X509Certificates.X509KeyUsageFlags]::KeyEncipherment
    $request.CertificateExtensions.Add([System.Security.Cryptography.X509Certificates.X509KeyUsageExtension]::new($keyUsage, $false))

    $ekuCollection = [System.Security.Cryptography.OidCollection]::new()
    [void]$ekuCollection.Add([System.Security.Cryptography.Oid]::new("1.3.6.1.5.5.7.3.1", "Server Authentication"))
    $request.CertificateExtensions.Add([System.Security.Cryptography.X509Certificates.X509EnhancedKeyUsageExtension]::new($ekuCollection, $false))

    $notBefore = [System.DateTimeOffset]::UtcNow.AddMinutes(-5)
    $notAfter = $notBefore.AddDays($DaysValid)
    $certificate = $request.CreateSelfSigned($notBefore, $notAfter)
    try {
        [System.IO.File]::WriteAllText($certPath, $certificate.ExportCertificatePem())
        [System.IO.File]::WriteAllText($keyPath, $rsa.ExportPkcs8PrivateKeyPem())
    }
    finally {
        $certificate.Dispose()
    }
}
finally {
    $rsa.Dispose()
}

Write-Host "Created localhost TLS certificate: $certPath"
Write-Host "Created localhost TLS private key: $keyPath"
Write-Host "Set SSL_CERTFILE=certs/localhost.pem and SSL_KEYFILE=certs/localhost-key.pem in .env to enable HTTPS."