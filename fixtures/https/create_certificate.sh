#!/bin/bash

if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <CN>"
    exit 1
fi

CN="$1"
BASE=$(echo "$CN" | awk -F'.' '{print $1}')
SUBJECT="/C=FR/ST=Rhone-Alpes/L=Grenoble/O=Mirantis/OU=Fuel plugins/CN=$CN"

# We only check that openssl is available
OPENSSL=$(which openssl)
if [ "$?" -ne 0 ]; then
    echo "openssl: command not found"
    exit 1
fi

# First we create the private key
$OPENSSL genrsa -out "$BASE.key" 2048
if [ "$?" -ne 0 ]; then
    echo "Failed to create $BASE.key"
    exit 1
fi
echo "Creation of $BASE.key done"

# Then we create the certificate signing request for BASE
$OPENSSL req -new -key "$BASE.key" -out "$BASE.csr" -subj "$SUBJECT"
if [ "$?" -ne 0 ]; then
    echo "Failed to create the CSR $BASE.csr"
    exit 1
fi
echo "Creation of $BASE.csr done"

# Sign it with the CA root key
ROOTKEY=$(cat <<EOF
LS0tLS1CRUdJTiBSU0EgUFJJVkFURSBLRVktLS0tLQpNSUlKS2dJQkFBS0NBZ0VB
NDFRajIrdXJGYVNjQ0xhc0xjYkNpMXc3MkU2bUFlSHFCZmRWN1k0RmU1eCs3dUV4
CkpDWGF4WVVCbUgxZTBxaTdqS3FrS3oxa1ZnTk41cDhtUjVHeUdyUExBb1lNLzJm
dzlaMFZndWsyVXVMaENOd3MKaTlGODhoblpXRU5rRCtwZ1VCcmMySEgyWkY1bGlT
R2phY1NiMjY4cENJUUZCVFZzeDFvWWRES3JKT3h4VXNtVAozd2FKR1Rmc2dHZXla
M0cyb3l3dm5yRUdnT0t3Y1VleW1tbUdpZDBoaHNLR1lONEJEM1RBVVpuZnI0ZGtq
YU5BCmVHRGM5OFlsWU9zVytQT2RqMzJvOC81bFgxWEdRRm9VWkthTTE4bnBIZ1hp
S1lpVDkzWWpuMXY3a3MxZTR1T0cKTGtEUVVKWStyVmJGSFZ5MVVVVXYzTXpqMURx
YzVyYVhYSGd4Ti9BSlU5aC9vR0IvNGx6aXBLUlAwYXMxQVM3VwpINngxbkVuWGpS
YzZYcDY2bDdqbXRsTWtoNjN4QkFFbnlCY1JhYldqaUR3NEZUcUpDNWVwTi9iNDZu
M1hScEs2ClZSclZTR05HSFdBTjFFdTZoTzRiSTBTVHRoRmM5TXgvU2FhNUNHNGh0
QzJRZXl1allrbWxJblI3cS9tZldKeXoKZnJRTWY1QUkxU29MRDQrQk9LS2lhL1Zt
T2tZTGdSREgyWjZmT0ZBdHJYdHA2MnJzK2kyMXh4VUhrVmJDQ3NYaApLaGNHL1c4
WUZUSDJqVHp3aStKVCtXeFM0TnhOazBrTmdlNG1vQWVUQ3BLZTVIbnNXU2lvb1l0
RTEwV2JwN3VrCnJscnc4ZFQ5Z2hFaG5VenlyQVIxZ0YrMU1MNXUzV0drVUNSZTFP
VXVVbStVcEx5RUVzclBpN3FlaDJFQ0F3RUEKQVFLQ0FnRUFnQ3N5Ukk0czJYa0Rt
RTRWNllGRXNub0FLOGE4QmhldmNFbXhJc3lOL3RHUEozUEQxeE9Zc3dCNAprOWNy
blM0UkFCQTltenR6MUtMc1N2aTBCbW40dHVGanRqcUtIWDRtOXZQbjZ2VTk4YUdG
S3crbjlmVFlzMDhyCm9YM3RicVBBUmFtL2xqRTZzQUFnMHg0cUdqb0ZmZWpXQTcw
YmI0SmRvRkFGdFkzVHZHK3F2UGgxN0txc3BaRkkKUUdVMnl1ZnNCemVrYVo1NWdq
Vk5NYkV3MjZwZmRsODh4ZFByRzdaUGRyMW1xUnRPYUpLM2VMdndYMjZOWncxSwpp
Y2hDSFg2TStSZnFLQmJvWk1YaGp1cTYwTHl1Y0FPZzhaSnpudU1vT2I5YitqOU1L
Y3Fza3RPaEZYYnBmR1laClZIVzFrUVp5SEM0Yi9DdHcwSGx6ZVFpOWNoODU3N1Zu
eHZJWVo1V29nbnpuRHdTdjYwbHdYQTRiNVROTThSaS8KR3Rha2kzVFFrVTgvbjdy
WGhCTHdFRjZIbDJRZ0hjM2dUV2Z0blFBb2N5azgrUVgxTWp6ZG12dFFXcW1QWlZD
LwpqKytnQk9aV1BaTGtjUUtIMEtzSzljWUE0RXBhc1QydVhUdVN4L202c0VIdUdD
Sk0wY3NhZ21zVURGT2syaXZDCmpMayttSXNLM3d4dVhkTVI5VmYvRkszTS9ZcEZX
TjJBd1BFM1kzZnFJc1RYUUhLVHdZSDJDeHdGTE1oQmQvczYKWlE1VHUwNDgwMFZ5
cFhjdnI0QzlieU9vOTZlSWJoYVpYYm9GRVl2Ym1YazZSZ1hjYWZYVGVWbTlNUkRZ
V0N6dQpEVFkyS1Z4VjMwVWhCRXdXQ0s4U3pGbEhEb0pIUGVsTVh1eDQrN0RNRzE3
cTNCOVdYSUVDZ2dFQkFQOXFBeVFYCmV0UjVKNm1RaERubWlWVGR5dW9tdHhzTDhB
RkhrdnNtc1VydWpmYVpvaFFEYUtGZUUyb2pDZXdVZFNMNzJhYWUKZlFndWNQcGdz
cVFjVjRwdE5GWm9GTVJ4TUNUcW95N2xURUk3YkM3Ymp2aFh3N1ZhdjNiTFdVWVUv
N0xLeCtmMQpRaVFFSGNVU2s2bUtncDc5OXlnWFlrOERKd3NRS1laVEViSURZNXNZ
VzY0S1RBZ0EveFRNZTB3em9QbHFwc0s5CjdUSkpBOFRYMFNYL213T3l1V0wzK0xi
cnN5ZHFmMU1BKzlDTlZ3UFdpdy9ubm1ySnBxQVlLSVVQY0I4cTJ0WFMKTnI2bDZM
Smo4RGFmcS9CaTd2eWVxZCtHeFJudzlSQU8wV2x5cHBmakVUYU45OXVHQWZQcmRh
TGQzSnc5bzNRcAozdS83cGcrZ3UzejEwYWtDZ2dFQkFPUFpvcFdDM1VWTlBveTd3
WGptRXpBYzVLbnI3TVBrS1lqNjdNRHlUMDBYCkhMUENVNWgzeGgxVFcxbkNTWTJV
dWc2QkZTS2NkTllaeWFWT0tKcGNKbWwxb1BBZzc1d1d6NEp0dFRMckhZK1EKam5w
NlpxemROd2JPcEhVdU5RNVRjbmY0djFYalFKZUlKQ0Y3VlhBTTNET0MzekZjVlZI
UExWMm53amFhWGlndQp0ZVlKeHhzc0NodXptRDdseFVnRmpyTk1jRTcvMlNWYTJi
OWNDK1hHQktyL0oxdmx3OFloZC9KSEIvSnZwWnpVClEvK2lxOVJ6VGpEYXAwemhl
OU9sbnhKbzljNjE1c1hJeXVseUlqRUF5a1FaU1cyU0pMTEdtdE42QUxmeFhROTQK
NXRKbTR4TytGazU3VDZnc1ZlckNqVG15TE03Rm1lNDd4T0VwZjhuTkN2a0NnZ0VB
Y3BwQXVvc0doQnV3bmpiSAovYXJoYUFEMHNVZVoxVHJ2LzhMN3dsRkVMOWtHUGVZ
RmdYRmVHem01QUdDa2JSZG96Nyt0azBOOTJwUHNBWXd0CjI5RVR2bnJ0aHUvQWti
d3YzQUNrSThDakRQell0OVd3T3VJMllFTk5zYUhnZHIrcFU3SUZMS0V4Z2pPT29B
U0wKMlFEYlJ6ZXhGSDRaa0ZaYnlHMENGTkZsR1RqSUVxbEZTYnc1RFVaVkxpSHFH
UEQ1ZzdCRkR4QmxRN0RiVGhHQQpPTXFONVlUbUJmQTUydW03UXk1WDN3aUw5TEhX
bjFRK3BXNUorS1J1YlZzcG96cWdGbndHSVBibnRYZUFCN3NyCjUzYVJrWlR5b3Nz
V2NjTm80UkRyQkwrQld3MGtqdlpGblBMcWljZUJUTThUdzNaRkxKM0RuN1hCNEhC
THZLdGsKTk5lZnNRS0NBUUVBaWhxQTVGUjBuNnZKTE80a3Y0M2N0WDNkejJ5VGpz
eDlyR3hERWxRTVl2S09VQnFLSnRENgpRUTRrUVl4MG5wODJBdEtVcCt6akdGNTdE
WG9KUEQ1OGZkRnhZZnJrb054bW5HeTR0b3N4MkxISzJrdlViaFNMClpOSGRkclV5
TFdQQTd4elRoRkNBOXhmcXBteW1CWXVWOEpiemgyeXF2akp3RWVNNzRYTEJmV09L
bDByMzV1MVQKbHlUTk05cDdNRU5HRWtGVGxWNllGSDh6bWp4RmJka1BQVUg0Ymtn
ZTJMbXloU1F1bWZDNEZnM0d4V3lvNzlXUAo0Q2EzM3U2UTZtRHB3UFBqZ1k1WnVT
b1NhMXJsaElReEZRT3FzUUl5d2pXRTVJZC9aZjZpNUZ6b3MwRHZoQ2prClJsK1Jr
YUtGMVF4bEkwSnV6RW1UR29ZWnVFdzZDMnYvcVFLQ0FRRUFyZk1uZnFCUWZpeDZx
REVhZkM5TmRLOEcKaFBoR0ljZ1ZBVmdiVHZ5MGhGWC92c2UrbFJpOURwR21ZVDMr
cy95MU5QS1dueXBBYWlxRnFQTW5sU3YyU3RoZwo2am1pMFBRNEtNQUJFeGtvK0pT
dUZDYTNhWDVQMXg3NnB0c1l4KzVoV1VWcXlFem55UEt4dmNhN1ZQODBPaFROCktv
UVVuNGcvelhlSjVZZ21lL1VQYmMrSWtXUnN5VzQ5V3ZKWE5KQVNieEVwYldWT0Uy
VzVudFFTMWMzSjNBMUMKZHRseis3REhLUVFmUUJBL2YzWmFGZFFDaDZUMllqanBR
V0wycklJS2M1ZzZXTXJjL0c1YjNLSVdzdXBDVTQrQwp0aDRhMlR2WXdwczFyUFhG
d2VCWFl4bWNkbnpJWkZhZUNYbk10aVpWYWZlaHVNeVp2SzFta3kyajg2NkdmQT09
Ci0tLS0tRU5EIFJTQSBQUklWQVRFIEtFWS0tLS0tCg==
EOF
)

ROOTPEM=$(cat <<EOF
LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUdKVENDQkEyZ0F3SUJBZ0lK
QUkwQUtNZzFYMWt6TUEwR0NTcUdTSWIzRFFFQkN3VUFNSUduTVFzd0NRWUQKVlFR
R0V3SkdVakVVTUJJR0ExVUVDQXdMVW1odmJtVXRRV3h3WlhNeEVUQVBCZ05WQkFj
TUNFZHlaVzV2WW14bApNUkV3RHdZRFZRUUtEQWhOYVhKaGJuUnBjekVUTUJFR0Ex
VUVDd3dLVTNSaFkydE1hV2RvZERFaU1DQUdBMVVFCkF3d1pVM1JoWTJ0TWFXZG9k
Q0JTYjI5MElFRjFkR2h2Y21sMGVURWpNQ0VHQ1NxR1NJYjNEUUVKQVJZVWJXbHkK
WVc1MGFYTkFaWGhoYlhCc1pTNWpiMjB3SUJjTk1UWXdOakl6TVRRME16TXdXaGdQ
TXpBeE5URXdNalV4TkRRegpNekJhTUlHbk1Rc3dDUVlEVlFRR0V3SkdVakVVTUJJ
R0ExVUVDQXdMVW1odmJtVXRRV3h3WlhNeEVUQVBCZ05WCkJBY01DRWR5Wlc1dllt
eGxNUkV3RHdZRFZRUUtEQWhOYVhKaGJuUnBjekVUTUJFR0ExVUVDd3dLVTNSaFky
dE0KYVdkb2RERWlNQ0FHQTFVRUF3d1pVM1JoWTJ0TWFXZG9kQ0JTYjI5MElFRjFk
R2h2Y21sMGVURWpNQ0VHQ1NxRwpTSWIzRFFFSkFSWVViV2x5WVc1MGFYTkFaWGho
YlhCc1pTNWpiMjB3Z2dJaU1BMEdDU3FHU0liM0RRRUJBUVVBCkE0SUNEd0F3Z2dJ
S0FvSUNBUURqVkNQYjY2c1ZwSndJdHF3dHhzS0xYRHZZVHFZQjRlb0Y5MVh0amdW
N25IN3UKNFRFa0pkckZoUUdZZlY3U3FMdU1xcVFyUFdSV0EwM21ueVpIa2JJYXM4
c0NoZ3ovWi9EMW5SV0M2VFpTNHVFSQozQ3lMMFh6eUdkbFlRMlFQNm1CUUd0ellj
ZlprWG1XSklhTnB4SnZicnlrSWhBVUZOV3pIV2hoME1xc2s3SEZTCnlaUGZCb2ta
Tit5QVo3Sm5jYmFqTEMrZXNRYUE0ckJ4UjdLYWFZYUozU0dHd29aZzNnRVBkTUJS
bWQrdmgyU04KbzBCNFlOejN4aVZnNnhiNDg1MlBmYWp6L21WZlZjWkFXaFJrcG96
WHlla2VCZUlwaUpQM2RpT2ZXL3VTelY3aQo0NFl1UU5CUWxqNnRWc1VkWExWUlJT
L2N6T1BVT3B6bXRwZGNlREUzOEFsVDJIK2dZSC9pWE9La3BFL1JxelVCCkx0WWZy
SFdjU2RlTkZ6cGVucnFYdU9hMlV5U0hyZkVFQVNmSUZ4RnB0YU9JUERnVk9va0xs
NmszOXZqcWZkZEcKa3JwVkd0VklZMFlkWUEzVVM3cUU3aHNqUkpPMkVWejB6SDlK
cHJrSWJpRzBMWkI3SzZOaVNhVWlkSHVyK1o5WQpuTE4rdEF4L2tBalZLZ3NQajRF
NG9xSnI5V1k2Umd1QkVNZlpucDg0VUMydGUybnJhdXo2TGJYSEZRZVJWc0lLCnhl
RXFGd2I5YnhnVk1mYU5QUENMNGxQNWJGTGczRTJUU1EyQjdpYWdCNU1La3A3a2Vl
eFpLS2loaTBUWFJadW4KdTZTdVd2RHgxUDJDRVNHZFRQS3NCSFdBWDdVd3ZtN2RZ
YVJRSkY3VTVTNVNiNVNrdklRU3lzK0x1cDZIWVFJRApBUUFCbzFBd1RqQWRCZ05W
SFE0RUZnUVV2Um9qNVBZcFQ3bzBYSmVMSnhOM3FFbE13ZzB3SHdZRFZSMGpCQmd3
CkZvQVV2Um9qNVBZcFQ3bzBYSmVMSnhOM3FFbE13ZzB3REFZRFZSMFRCQVV3QXdF
Qi96QU5CZ2txaGtpRzl3MEIKQVFzRkFBT0NBZ0VBUU5VT3JkRkIrVmtjUmUwVEVj
cmE5aWJ4WDRIOUpDR0xWZXdYMjlkQXdhRXltYnJRZzFlOAphbXhWK1hxck1GbVVF
OVZMZEVDQnowREhyRXFTTW5HYUl0ZHBzVE9tQTRrOG9QSy9xV1NrdmcwcWpBdVRO
K1RWCnU5YWpPL1kzSG9RM1dXYnhFZHFCOE9ycFpuV0plOW1PckdNU1ZkRVVsWllk
R1BwcmtVd0M5TlBzUHRVSGl0bHIKUEJxKzMvcm5oN29uV2VyQUpza0VQWTliVFAy
K3RSNjQzOEtUUnIzVFgvMzdzNEtxb3Qrbm5DOVJCUkhCQjlregpjZisrNHluQ2tk
dzFSYzNRYXlGU3lvcjB0akU2LzVtRXBuSEJPb0MzdTZ0VHZ6NCtYUE5uUnArSkJM
Z1J1OUhZCk0vQ3JOTnhWMEIzWnE1NmtZNjNHVU9iODdnVlpWejFOVURySktYak1x
a3FJT3lQbWlXNjBTeURiblM5V2crK2gKYy9FVmNCL0lieXN1WSswSXphSFJUc0wr
ajlOUlU5cmd1cnhxcG5WVzhoOEp2cEx5RnM2cDdzM0FEbTFPVFovTgpuSWVhbzk0
bCtRaWpmSThQd0NTeER2TWQwdjRLa3laWEZjeGFJL2lMU3dSSHdjaDBjK252TjhX
bVpCY3lQMDJwClBnSFU5V1JxMXJoTWp0aHlDd3hlajc1YkdqRCtieHJ0amZuMGJa
MEFTQ29FMFRYZ0xvdTlVakV0a2V4dmhIaUsKRC9kZGNTN1BqUDVlVXlhc1plYUhj
bjIzN1ZZbmEzVFdsWTZMdzlSTnNINnZ2ZWVSNXBIZVQ0cFVtRDdXYnlBQgpZNlhG
S3RnWGt3aVl3NTExTWJWSjFQYS9vYjZkQktWUEVLMUwyWS9GancxdzNnWFc0cHhF
cnRrPQotLS0tLUVORCBDRVJUSUZJQ0FURS0tLS0tCg==
EOF
)

ROOTKEYFILE=$(mktemp -t rootCA-XXX.key)
ROOTPEMFILE=$(mktemp -t rootCA-XXX.pem)

echo "$ROOTKEY" | $OPENSSL base64 -d -out "$ROOTKEYFILE"
echo "$ROOTPEM" | $OPENSSL base64 -d -out "$ROOTPEMFILE"

# Verify the checksum
MD5FILE=$(mktemp -t md5-XXX)
echo "8e3c74e6a6f143c902540968fce833d2 $ROOTKEYFILE
9f9813ac87039b621d50a47d20cc3568 $ROOTPEMFILE" > "$MD5FILE"

md5sum -c "$MD5FILE"
if [ "$?" -ne 0 ]; then
    echo "Failed to validate checksum for $ROOTKEYFILE/$ROOTPEMFILE"
    exit 1
fi

$OPENSSL x509 -req -in "$BASE.csr" \
    -CAkey "$ROOTKEYFILE" \
    -CA "$ROOTPEMFILE" \
    -CAcreateserial -out "$BASE.crt" -days 500 -sha256
if [ "$?" -ne 0 ]; then
    echo "Failed to create the signed certificate $BASE.crt"
    exit 1
fi
echo "Creation of $BASE.crt done"

# Concatenate file
cat "$BASE.crt" "$BASE.key" > "$BASE.pem"
echo "Creation of $BASE.pem done"

# Cleanup
rm -f "$BASE.key" "$BASE.csr" "$BASE.crt"
rm -f "$ROOTKEYFILE" "$ROOTPEMFILE" "$MD5FILE"
