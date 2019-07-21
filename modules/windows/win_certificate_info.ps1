#!powershell

# Copyright: (c) 2019, sky-joker
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

#AnsibleRequires -CSharpUtil Ansible.Basic

$spec = @{
    options = @{
        regexp = @{ type = "str"; required = $true; }
        cert_store_location = @{ type = "str"; required = $true; }
    }
    supports_check_mode = $false
}
$module = [Ansible.Basic.AnsibleModule]::Create($args, $spec)

Function New-CertsResultStructure($certificates, $certs_result) {

    foreach($certificate in $certificates) {
        $certs_result.Add(@{
            Version = $certificate.Version
            Subject = $certificate.Subject
            Issuer = $certificate.Issuer
            Thumbprint = $certificate.Thumbprint
            FriendlyName = $certificate.FriendlyName
            NotBefore = $certificate.NotBefore.ToString("yyyyMMdd")
            NotAfter = $certificate.NotAfter.ToString("yyyyMMdd")
            EnhancedKeyUsageList = $certificate.EnhancedKeyUsageList
            DnsNameList = $certificate.DnsNameList
            SignatureAlgorithm = $certificate.SignatureAlgorithm
            SerialNumber = $certificate.SerialNumber
            PurivateKey = @{
                PublicOnly = $certificate.PrivateKey.PublicOnly
                KeySize = $certificate.PrivateKey.KeySize
                KeyExchangeAlgorithm = $certificate.PrivateKey.KeyExchangeAlgorithm
            }
            PublicKey = @{
                PublicOnly = $certificate.Publickey.Key.PublicOnly
                KeySize = $certificate.PublicKey.Key.KeySize
                KeyExchangeAlgorithm = $certificate.PublicKey.Key.KeyExchangeAlgorithm
            }
            Archived = $certificate.Archived
        })

    }

    return ,$certs_result
}

$regexp = $module.Params.regexp
$cert_store_location = $module.Params.cert_store_location

Set-Location $cert_store_location

$certs_result = New-Object System.Collections.Generic.List[HashTable]
$certificates = Get-ChildItem | Where-Object { $_.Subject -like "$regexp" }

if($certificates) {
    $certs_result = New-CertsResultStructure $certificates $certs_result
}

$module.Result.certs_info = $certs_result
$module.Result.changed = $false
$module.ExitJson()
