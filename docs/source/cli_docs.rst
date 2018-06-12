.. AUTO-GENERATED FILE - DO NOT EDIT!! Use `make cli_docs`.
   ==============================================================
CLI
==============================================================

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Module: treadmill_aws.cli.admin
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
::

                Usage: run [OPTIONS] COMMAND [ARGS]...

                Options:
                  --help  Show this message and exit.

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Module: treadmill_aws.cli.admin.aws
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
::

                Usage: aws [OPTIONS] COMMAND [ARGS]...

                  Manage AWS

                Options:
                  --aws-region TEXT
                  --aws-profile TEXT
                  --ipa-domain TEXT
                  --ipa-certs TEXT
                  --help              Show this message and exit.

                Commands:
                  image     Manage image configuration
                  instance  Manage instance configuration
                  secgroup  Manage security group configuration.
                  subnet    Manage subnet configuration
                  user      Manage user configuration
                  vpc       Manage vpc configuration

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Module: treadmill_aws.cli.admin.aws.image
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
::

                Usage: image [OPTIONS] COMMAND [ARGS]...

                  Manage image configuration

                Options:
                  --help  Show this message and exit.

                Commands:
                  configure  Configure AMI image.
                  create     Create image
                  list       List images
                  share      Share Image



                Usage: image configure [OPTIONS] [IMAGE]

                  Configure AMI image.

                Options:
                  --account TEXT  Image account, defaults to current.
                  --help          Show this message and exit.

                Usage: image create [OPTIONS] IMAGE

                  Create image

                Options:
                  --base-image IMAGE         Base image.  [required]
                  --base-image-account TEXT  Base image account.
                  --userdata PATH            Cloud-init user data.  [required]
                  --instance-profile TEXT    IAM profile with create image privs.  [required]
                  --secgroup SECGROUP        Security group  [required]
                  --subnet SUBNET            Subnet  [required]
                  --key TEXT                 SSH key  [required]
                  --help                     Show this message and exit.

                Usage: image list [OPTIONS] [IMAGE]

                  List images

                Options:
                  --account TEXT  Image account, defaults to current.
                  --help          Show this message and exit.

                Usage: image share [OPTIONS] IMAGE

                  Share Image

                Options:
                  --account TEXT  Account ID.  [required]
                  --help          Show this message and exit.

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Module: treadmill_aws.cli.admin.aws.instance
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
::

                Usage: instance [OPTIONS] COMMAND [ARGS]...

                  Manage instance configuration

                Options:
                  --help  Show this message and exit.

                Commands:
                  configure  Configure instance
                  create     Create instance(s)
                  delete     Delete instance.
                  list       List instances



                Usage: instance configure [OPTIONS] [INSTANCE]

                  Configure instance

                Options:
                  --help  Show this message and exit.

                Usage: instance create [OPTIONS]

                  Create instance(s)

                Options:
                  --image IMAGE         Image
                  --image-account TEXT  AWS image account.
                  --secgroup SECGROUP   Security group
                  --subnet SUBNET       Subnet
                  --role TEXT           Instance role
                  --key TEXT            Instance SSH key name
                  --size TEXT           Instance EC2 size  [required]
                  --count INTEGER       Number of instances  [required]
                  --disk-size TEXT      Root parition size, e.g. 100G  [required]
                  --help                Show this message and exit.

                Usage: instance delete [OPTIONS] HOSTNAME

                  Delete instance.

                Options:
                  --help  Show this message and exit.

                Usage: instance list [OPTIONS]

                  List instances

                Options:
                  --help  Show this message and exit.

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Module: treadmill_aws.cli.admin.aws.secgroup
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
::

                Usage: secgroup [OPTIONS] COMMAND [ARGS]...

                  Manage security group configuration.

                Options:
                  --help  Show this message and exit.

                Commands:
                  configure  Configure security group.
                  list       List security groups



                Usage: secgroup configure [OPTIONS] [SECGRP]

                  Configure security group.

                Options:
                  --help  Show this message and exit.

                Usage: secgroup list [OPTIONS]

                  List security groups

                Options:
                  --help  Show this message and exit.

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Module: treadmill_aws.cli.admin.aws.subnet
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
::

                Usage: subnet [OPTIONS] COMMAND [ARGS]...

                  Manage subnet configuration

                Options:
                  --help  Show this message and exit.

                Commands:
                  configure  Configure subnet
                  list       List subnets



                Usage: subnet configure [OPTIONS] [SUBNET]

                  Configure subnet

                Options:
                  --help  Show this message and exit.

                Usage: subnet list [OPTIONS]

                  List subnets

                Options:
                  --help  Show this message and exit.

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Module: treadmill_aws.cli.admin.aws.user
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
::

                Usage: user [OPTIONS] COMMAND [ARGS]...

                  Manage user configuration

                Options:
                  --help  Show this message and exit.

                Commands:
                  configure  Create user.
                  delete     Delete user.
                  list       List users.



                Usage: user configure [OPTIONS] USERNAME

                  Create user.

                Options:
                  --usertype [proid|user|privuser]
                                                  User type.
                  --fname TEXT                    First Name.
                  --lname TEXT                    Last Name.
                  --policy-doc TEXT               IAM Role policy document.
                  --kadmin TEXT                   IPA kadmin principal.
                  --ktadmin TEXT                  IPA kadmin keytab file.
                  --help                          Show this message and exit.

                Usage: user delete [OPTIONS] USERNAME

                  Delete user.

                Options:
                  --help  Show this message and exit.

                Usage: user list [OPTIONS]

                  List users.

                Options:
                  --help  Show this message and exit.

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Module: treadmill_aws.cli.admin.aws.vpc
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
::

                Usage: vpc [OPTIONS] COMMAND [ARGS]...

                  Manage vpc configuration

                Options:
                  --help  Show this message and exit.

                Commands:
                  configure  Configure vpc
                  list       List vpcs



                Usage: vpc configure [OPTIONS] [VPC]

                  Configure vpc

                Options:
                  --help  Show this message and exit.

                Usage: vpc list [OPTIONS]

                  List vpcs

                Options:
                  --help  Show this message and exit.

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Module: treadmill_aws.cli.aws
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
::

                Usage: aws [OPTIONS] COMMAND [ARGS]...

                  Manage AWS

                Options:
                  --help  Show this message and exit.

                Commands:
                  image  Manage Treadmill app monitor configuration

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Module: treadmill_aws.cli.aws.image
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
::

                Usage: image_group [OPTIONS] COMMAND [ARGS]...

                  Manage Treadmill app monitor configuration

                Options:
                  --api URL  API url to use.
                  --help     Show this message and exit.

                Commands:
                  configure  Configure AWS image.
                  delete     Delete AWS image
                  list       List AWS images.



                Usage: image_group configure [OPTIONS] NAME

                  Configure AWS image.

                Options:
                  --help  Show this message and exit.

                Usage: image_group delete [OPTIONS] NAME

                  Delete AWS image

                Options:
                  --help  Show this message and exit.

                Usage: image_group list [OPTIONS]

                  List AWS images.

                Options:
                  --help  Show this message and exit.

