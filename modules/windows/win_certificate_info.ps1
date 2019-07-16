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

$regexp = $module.Params.regexp
$CertStoreLocation = $module.Params.cert_store_location

Set-Location $CertStoreLocation
$Certificate = Get-ChildItem | Where-Object { $_.Subject -like "*$regexp*" }

if($Certificate) {
    $module.Result.Subject = $Certificate.Subject
    $module.Result.Issuer = $Certificate.Issuer
    $module.Result.Thumbprint = $Certificate.Thumbprint
    $module.Result.FriendlyName = $Certificate.FriendlyName
    $module.Result.NotBefore = $Certificate.NotBefore.ToString("yyyyMMdd")
    $module.Result.NotAfter = $Certificate.NotAfter.ToString("yyyyMMdd")
}

$module.Result.changed = $false
$module.ExitJson()
