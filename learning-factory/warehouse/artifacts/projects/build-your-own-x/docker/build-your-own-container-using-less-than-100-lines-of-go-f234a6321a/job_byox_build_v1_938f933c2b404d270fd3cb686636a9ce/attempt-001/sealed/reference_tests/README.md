# Sealed reference tests

The default suite is deterministic and side-effect free beyond temporary directories. It tests the
complete validation, parser, codec, and launch-plan contracts.

```text
go test ./...
```

`TestIntegrationProbe` is skipped unless all of the following are true:

- the host is Linux;
- `TINYCONTAINER_INTEGRATION_ROOTFS` names an absolute rootfs prepared by
  `environment/make-rootfs.sh`; and
- the operator has chosen a disposable host whose kernel permits the requested namespaces.

Set `TINYCONTAINER_INTEGRATION_USERNS=false` only when intentionally testing as a user that already
has the necessary capabilities. An integration pass is still not a security certification.
