"""Contains definitions for Residual Networks.

Residual networks were originally proposed in KaXS15_ . Then they improve the KaXS16_ 
Here we refer to the settings in KaXS15_ as `v1` and KaXS16_  as `v2`.

Since `torchvision resnet <https://github.com/pytorch/vision/blob/master/torchvision/models/resnet.py>`_ 
has already implemented 

* ResNet-18
* ResNet-34
* ResNet-50
* ResNet-101
* ResNet-152

for image net. Here we only implemented the remaining models 

* ResNet-20
* ResNet-32
* ResNet-44
* ResNet-56 

for CIFAR-10 dataset. Besides, their implementation uses projection shortcut by default. 


.. rubric:: References

.. [KaXS15] Kaiming He, Xiangyu Zhang, Shaoqing Ren, Jian Sun 
    Deep Residual Learning for Image Recognition. arXiv:1512.03385

.. [KaXS16] Kaiming He, Xiangyu Zhang, Shaoqing Ren, Jian Sun
    Identity Mappings in Deep Residual Networks. arXiv: 1603.05027

"""

import torch
import torch.nn as nn
from torch.nn import functional as F
_DEFAULT_RESNETCIFAR_VERSION = 1


def batch_norm(num_features):
    """Create a batch normalization layer.

    See the Disclaimers in Kaiming's 
    `github repository <https://github.com/KaimingHe/deep-residual-networks/tree/a7026cb6d478e131b765b898c312e25f9f6dc031>`_

    * they compute the mean and variance on a sufficiently large traing batch instead of moving average;
    * they learn gamma and beta in affine function.

    :param num_features: number of features passed to batch normalization
    :type num_features: int
    """
    return nn.BatchNorm2d(num_features=num_features, eps=1e-05, momentum=0, affine=True, track_running_stats=False)


def conv3x3(in_channels, out_channels, stride=1):
    """3x3 convolution with padding."""
    return nn.Conv2d(in_channels, out_channels, kernel_size=3, stride=stride, padding=1, bias=False)


class BasicBlockV1(nn.Module):
    """The basic block in KaXS15_ is used for shallower ResNets.

    The activation functions (ReLU and BN) are viewed as post-activation of the weight layer.

    .. note::
        This class is similar to `BasicBlock` in
        `resnet <https://github.com/pytorch/vision/blob/master/torchvision/models/resnet.py>`_.
        but with different nn.BatchNorm2d configuration.
    """

    def __init__(self, in_channels, out_channels, stride=1, downsample=None):
        """
        :param in_channels: input channels
        :type in_channels: int
        :param out_channels: output channels
        :type out_channels: int
        :param stride: stride of the first layer, defaults to 1
        :type stride: int, optional
        :param downsample: projection identity map or no downsample, defaults to None
        :type downsample: nn.module or None, optional
        """
        super(BasicBlockV1, self).__init__()

        self.conv1 = conv3x3(in_channels, out_channels, stride)
        self.bn1 = batch_norm(out_channels)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = conv3x3(out_channels, out_channels)
        self.bn2 = batch_norm(out_channels)
        self.downsample = downsample
        self.stride = stride

    def forward(self, x):
        residual = self.downsample(x) if self.downsample is not None else x

        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)
        out = self.conv2(out)
        out = self.bn2(out)

        # Shortcut connection.
        out += residual
        out = self.relu(out)
        return out


class BasicBlockV2(nn.Module):
    """The basic block in KaXS16_ is used for shallower ResNets.

    The activation functions (ReLU and BN) are viewed as pre-activation of the weight layer.
    """

    def __init__(self, in_channels, out_channels, stride=1, downsample=None):
        """
        :param in_channels: input channels
        :type in_channels: int
        :param out_channels: output channels
        :type out_channels: int
        :param stride: stride of the first layer, defaults to 1
        :type stride: int, optional
        :param downsample: projection identity map or no downsample, defaults to None
        :type downsample: nn.module or None, optional
        """
        super(BasicBlockV2, self).__init__()

        self.bn1 = batch_norm(in_channels)
        self.relu = nn.ReLU(inplace=True)
        self.conv1 = conv3x3(in_channels, out_channels, stride)
        self.bn2 = batch_norm(out_channels)
        self.conv2 = conv3x3(out_channels, out_channels)
        self.downsample = downsample
        self.stride = stride

    def forward(self, x):
        residual = self.downsample(x) if self.downsample is not None else x

        out = self.bn1(x)
        out = self.relu(out)
        out = self.conv1(out)
        out = self.bn2(out)
        out = self.relu(out)
        out = self.conv2(out)

        # Shortcut connection.
        out += residual
        return out


class BottleneckBlockV1(nn.Module):
    """Bottleneck building block proposed in KaXS15_ (post-activation)."""
    pass


class BottleneckBlockV2(nn.Module):
    """Bottleneck building block proposed in KaXS16_ (post-activation)."""
    pass


class ResNetCIFAR(nn.Module):
    """
    The ResNet struction defined in KaXS15_ and KaXS16_.

    For CIFAR-10 dataset, the ResNet are configured to have 6n+2 layers where fixing n={3,5,7,9}
    gives ResNet-20,32,44,56 seperately. The input image is assumed to have a shape of 32*32 pixels.
    """

    def __init__(self, resnet_size, bottleneck, num_classes, version=_DEFAULT_RESNETCIFAR_VERSION):
        super(ResNetCIFAR, self).__init__()

        if resnet_size % 6 != 2:
            raise ValueError("The resnet_size should be (6 * num_blocks + 2). Got {}."
                             .format(resnet_size))

        num_blocks = (resnet_size - 2) // 6

        if version not in (1, 2):
            raise ValueError("Resnet version should be 1 or 2, got {}.".format(version))

        if bottleneck:
            raise NotImplementedError
        else:
            if version == 1:
                block = BasicBlockV1
            elif version == 2:
                block = BasicBlockV2
            else:
                raise NotImplementedError

        # The first layer
        if version == 1 or version == 2:
            self.prep = nn.Sequential(
                conv3x3(in_channels=3, out_channels=16, stride=1),
                batch_norm(num_features=16),
                nn.ReLU())
        else:
            raise NotImplementedError

        # 6n layers
        self.conv_1 = self._make_layer(block, in_channels=16, out_channels=16,
                                       num_blocks=num_blocks, init_stride=1)
        self.conv_2 = self._make_layer(block, in_channels=16, out_channels=32,
                                       num_blocks=num_blocks, init_stride=2)
        self.conv_3 = self._make_layer(block, in_channels=32, out_channels=64,
                                       num_blocks=num_blocks, init_stride=2)

        # Add an average pooling layer:
        # the output of conv_3 has shape H=W=8
        # the output average pooling will be (batch_size, channels, 1, 1)
        self.avgpool = nn.AvgPool2d(8, stride=1)

        self.classifier = nn.Linear(in_features=64, out_features=num_classes, bias=True)

        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)

    def _make_layer(self, block, in_channels, out_channels, num_blocks, init_stride=1):
        """Create a block of 2*n depth.

        .. note::
            In KaXS15_ there are two types of shortcuts: identity and projection. Here we use the following:
            * identity shortcut for same number of channels
            * projection shortcut for increasing number of channels

        """
        # by the design of ResNet, if the init_stride > 1, then out_channels > in_channels.
        # For project shortcut, the extra channels are created using a 1*1 convolution.
        # For identity shortcut, zeros are padded.
        if init_stride == 1:
            downsample = None
        else:
            # Use projection when the dimension of channel increases.
            downsample = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, kernel_size=1, stride=init_stride, bias=False),
                batch_norm(num_features=out_channels))

        # Maybe use downsample in the first block.
        layers = [block(in_channels, out_channels, stride=init_stride, downsample=downsample)]
        for i in range(1, num_blocks):
            layers.append(block(out_channels, out_channels))

        return nn.Sequential(*layers)

    def forward(self, x):
        x = self.prep(x)
        x = self.conv_1(x)
        x = self.conv_2(x)
        x = self.conv_3(x)
        x = self.avgpool(x)

        # The plane has shape (1, 1)
        x = x.view(x.size(0), -1)
        x = self.classifier(x)
        return x


################################################################################################################

class PreActBlock(nn.Module):

    def __init__(self, in_channels, out_channels, stride=1):
        super(PreActBlock, self).__init__()

        self.bn1 = nn.BatchNorm2d(in_channels)
        self.conv1 = nn.Conv2d(in_channels, out_channels, kernel_size=3, stride=stride, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(out_channels)
        self.conv2 = nn.Conv2d(out_channels, out_channels, kernel_size=3, stride=1, padding=1, bias=False)

        if stride != 1 or in_channels != out_channels:
            self.shortcut = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, kernel_size=1, stride=stride, bias=False)
            )

    def forward(self, x):
        out = F.relu(self.bn1(x))
        shortcut = self.shortcut(out) if hasattr(self, 'shortcut') else x
        out = self.conv1(out)
        out = self.conv2(F.relu(self.bn2(out)))
        return out + shortcut


class ResNet18_CIFAR10(nn.Module):

    def __init__(self, layers, num_classes=1000):
        super(ResNet18_CIFAR10, self).__init__()
        self.prep = nn.Sequential(
            nn.Conv2d(3, 64, kernel_size=3, stride=1, padding=1, bias=False),
            nn.BatchNorm2d(64),
            nn.ReLU()
        )

        self.layers = nn.Sequential(
            self._make_layer(64, 64, layers[0], stride=1),
            self._make_layer(64, 128, layers[1], stride=2),
            self._make_layer(128, 256, layers[2], stride=2),
            self._make_layer(256, 256, layers[3], stride=2),
        )

        self.classifier = nn.Linear(512, num_classes)

    def _make_layer(self, in_channels, out_channels, num_blocks, stride):

        strides = [stride] + [1] * (num_blocks-1)
        layers = []
        for stride in strides:
            layers.append(PreActBlock(in_channels=in_channels, out_channels=out_channels, stride=stride))
            in_channels = out_channels

        return nn.Sequential(*layers)

    def forward(self, x):
        x = self.prep(x)

        x = self.layers(x)

        x_avg = F.adaptive_avg_pool2d(x, (1, 1))
        x_avg = x_avg.view(x_avg.size(0), -1)

        x_max = F.adaptive_max_pool2d(x, (1, 1))
        x_max = x_max.view(x_max.size(0), -1)

        x = torch.cat([x_avg, x_max], dim=-1)

        x = self.classifier(x)

        return x


def resnet18_bkj(options):
    """Constructs a ResNet-18 model from DAWN.

    This 
    `implementation <https://github.com/bkj/basenet/blob/49b2b61e5b9420815c64227c5a10233267c1fb14/examples/cifar10.py>`_
    comes from which gives results in 
    `DAWNBench <https://github.com/stanford-futuredata/dawn-bench-entries/blob/master/CIFAR10/train/basenet.json>`_.
    """
    model = ResNet18_CIFAR10([2, 2, 2, 2], num_classes=options.num_classes)
    return model


def get_model(options):
    if options.model_name == 'resnet18':
        if options.model_version == 'default':
            return resnet18_bkj(options)
    elif options.model_name in ['resnet20', 'resnet32', 'resnet44', 'resnet56'] and options.dataset_name == 'cifar10':
        resnet_size = int(options.model_name[-2:])
        version = int(options.model_version)
        return ResNetCIFAR(resnet_size, False, 10, version=version)

    raise NotImplementedError("{}_{} is not implemented.".format(
        options.model_name, options.model_version))
